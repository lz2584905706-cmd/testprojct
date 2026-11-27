r"""
验证后端对「数据库锁等待超时 1205」的降级能力

思路：人工开一个事务把目标行锁住不提交，让后端 UPDATE 卡在等锁上，
      等超过 innodb_lock_wait_timeout 后 MySQL 抛 1205，
      此时后端应自动重试一次，仍失败则返回 503 + Retry-After。

用法：.\.venv\Scripts\python.exe scripts\probe_503.py
注意：脚本会临时修改全局 innodb_lock_wait_timeout，结束时在 finally 里恢复。
"""
import sys
import threading
import time
import pymysql
import requests

BASE = "http://127.0.0.1:5000"
DB = dict(host="127.0.0.1", user="root", password="123456",
          database="my_user_api", charset="utf8mb4")
TEST_EMAIL = "probe_503@lockcheck.test"


def conn(autocommit=True):
    return pymysql.connect(**DB, autocommit=autocommit)


def get_token():
    r = requests.post(f"{BASE}/api/login",
                      json={"username": "admin", "password": "123456"}, timeout=5)
    r.raise_for_status()
    return r.json()["data"]["token"]


def set_global_timeout(value):
    c = conn()
    try:
        with c.cursor() as cur:
            cur.execute("SET GLOBAL innodb_lock_wait_timeout = %s", (value,))
    finally:
        c.close()


def main():
    c = conn()
    with c.cursor() as cur:
        cur.execute("SHOW VARIABLES LIKE 'innodb_lock_wait_timeout'")
        original = int(cur.fetchone()[1])
    c.close()
    print(f"原始 innodb_lock_wait_timeout = {original}")

    locker = None
    try:
        # 1. 把锁等待超时调到 2 秒，让实验在几秒内完成
        set_global_timeout(2)
        print("已临时设为 2 秒")

        # 2. 造一个专用用户
        headers = {"Authorization": f"Bearer {get_token()}"}
        r = requests.post(f"{BASE}/api/users",
                          json={"name": "probe_503", "email": TEST_EMAIL, "status": 1},
                          headers=headers, timeout=5)
        if r.status_code != 201:
            print(f"准备用户失败: {r.status_code} {r.text[:200]}")
            return 1
        uid = r.json()["data"]["id"]
        print(f"创建用户 id={uid}")

        # 3. 人工开事务锁住这一行，不提交
        locker = conn(autocommit=False)
        locker.begin()
        with locker.cursor() as cur:
            cur.execute("SELECT id FROM t_user WHERE id=%s FOR UPDATE", (uid,))
        print("目标行已锁定，开始发送 PUT 请求")

        # 4. 后台线程发请求，会被锁挡住
        result = {}

        def send():
            try:
                result["resp"] = requests.put(
                    f"{BASE}/api/users/{uid}",
                    json={"name": "should_block"},
                    headers=headers, timeout=30,
                )
            except Exception as e:
                result["err"] = repr(e)

        t = threading.Thread(target=send)
        t.start()

        # 5. 等“两次 1205 + 一次退避”跑完
        time.sleep(6)

        # 6. 释放锁
        locker.rollback()
        locker.close()
        locker = None
        print("已释放锁")

        t.join(timeout=30)

        if "resp" not in result:
            print(f"请求异常: {result.get('err')}")
            return 1

        resp = result["resp"]
        print(f"HTTP 状态码: {resp.status_code}")
        print(f"Retry-After: {resp.headers.get('Retry-After')}")
        print(f"响应体: {resp.text[:200]}")

        ok = resp.status_code == 503 and resp.headers.get("Retry-After") is not None
        print("\n结论:", "503 降级 + Retry-After 生效" if ok else "未按预期返回 503")
        return 0 if ok else 1

    finally:
        if locker is not None:
            try:
                locker.rollback()
                locker.close()
            except Exception:
                pass
        try:
            set_global_timeout(original)
            print(f"已恢复 innodb_lock_wait_timeout = {original}")
        except Exception as e:
            print(f"!!! 恢复全局参数失败，请手工执行 SET GLOBAL innodb_lock_wait_timeout = {original}; {e}")
        try:
            c = conn()
            with c.cursor() as cur:
                cur.execute("DELETE FROM t_user WHERE email=%s", (TEST_EMAIL,))
            c.close()
            print("已清理测试用户")
        except Exception as e:
            print(f"清理失败: {e}")


if __name__ == "__main__":
    sys.exit(main())
