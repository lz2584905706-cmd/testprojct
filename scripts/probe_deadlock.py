r"""
MySQL 死锁复现探针（双模式）

用法：
  .\.venv\Scripts\python.exe scripts\probe_deadlock.py --mode swap    # 交叉交换唯一值
  .\.venv\Scripts\python.exe scripts\probe_deadlock.py --mode cross   # 行锁顺序交叉

两种模式的差别，正是「会报 1062」和「会报 1213」的分水岭：

mode=swap（10 线程改同一邮箱、两用户互换邮箱都属于这类）
  目标唯一值已存在，InnoDB 的唯一性检查直接判定冲突 -> 快速失败 1062
  多个请求只是单向排队，不成环，永远不会 1213

mode=cross（一个事务里更新多行，两个事务的加锁顺序相反）
  T1 持 A 锁等 B，T2 持 B 锁等 A -> 环形等待 -> InnoDB 死锁检测介入 -> 1213
"""
import argparse
import sys
import threading
import pymysql

DB = dict(
    host="127.0.0.1", user="root", password="123456",
    database="my_user_api", charset="utf8mb4", autocommit=False,
)

EMAIL_A = "probe_a@deadlock.test"
EMAIL_B = "probe_b@deadlock.test"


def new_conn():
    return pymysql.connect(**DB)


def prepare():
    c = new_conn()
    try:
        with c.cursor() as cur:
            cur.execute("DELETE FROM t_user WHERE email IN (%s, %s)", (EMAIL_A, EMAIL_B))
            cur.execute(
                "INSERT INTO t_user (name, email, status) VALUES "
                "('probe_a', %s, 1), ('probe_b', %s, 1)",
                (EMAIL_A, EMAIL_B),
            )
        c.commit()
        with c.cursor() as cur:
            cur.execute(
                "SELECT id, email FROM t_user WHERE email IN (%s, %s) ORDER BY email",
                (EMAIL_A, EMAIL_B),
            )
            rows = cur.fetchall()
        return rows[0][0], rows[1][0]
    finally:
        c.close()


def cleanup():
    c = new_conn()
    try:
        with c.cursor() as cur:
            cur.execute("DELETE FROM t_user WHERE email IN (%s, %s)", (EMAIL_A, EMAIL_B))
        c.commit()
    finally:
        c.close()


def run_swap(id_a, id_b, results):
    """交叉交换唯一值：两边都只会拿到 1062"""
    barrier = threading.Barrier(2)

    def worker(tag, my_id, target_email, name):
        conn = new_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE t_user SET name=%s WHERE id=%s", (name, my_id))
                barrier.wait(timeout=10)
                cur.execute("UPDATE t_user SET email=%s WHERE id=%s", (target_email, my_id))
            conn.commit()
            results[tag] = ("success", None)
        except pymysql.err.OperationalError as e:
            conn.rollback()
            results[tag] = ("OperationalError", e.args[0])
        except pymysql.err.IntegrityError as e:
            conn.rollback()
            results[tag] = ("IntegrityError", e.args[0])
        except Exception as e:
            conn.rollback()
            results[tag] = (type(e).__name__, str(e))
        finally:
            conn.close()

    t1 = threading.Thread(target=worker, args=("T1", id_a, EMAIL_B, "t1"))
    t2 = threading.Thread(target=worker, args=("T2", id_b, EMAIL_A, "t2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def run_cross(id_a, id_b, results):
    """行锁顺序交叉：必然死锁"""
    barrier = threading.Barrier(2)

    def worker(tag, first_id, second_id):
        conn = new_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE t_user SET name=%s WHERE id=%s", (f"{tag}_first", first_id))
                barrier.wait(timeout=10)
                cur.execute("UPDATE t_user SET name=%s WHERE id=%s", (f"{tag}_second", second_id))
            conn.commit()
            results[tag] = ("success", None)
        except pymysql.err.OperationalError as e:
            conn.rollback()
            results[tag] = ("OperationalError", e.args[0])
        except Exception as e:
            conn.rollback()
            results[tag] = (type(e).__name__, str(e))
        finally:
            conn.close()

    # T1 先锁 A 再锁 B，T2 先锁 B 再锁 A
    t1 = threading.Thread(target=worker, args=("T1", id_a, id_b))
    t2 = threading.Thread(target=worker, args=("T2", id_b, id_a))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["swap", "cross"], default="swap")
    args = parser.parse_args()

    id_a, id_b = prepare()
    print(f"准备完成: id_a={id_a}({EMAIL_A})  id_b={id_b}({EMAIL_B})  模式={args.mode}")

    results = {}
    if args.mode == "swap":
        run_swap(id_a, id_b, results)
    else:
        run_cross(id_a, id_b, results)

    print("结果:")
    for tag, (kind, detail) in sorted(results.items()):
        print(f"  {tag}: {kind} {detail if detail is not None else ''}")

    cleanup()

    err_codes = [d for (kind, d) in results.values() if kind == "OperationalError"]
    if 1213 in err_codes:
        print("\n结论: 触发 1213 死锁（环形等待成立）")
        return 0
    if err_codes:
        print(f"\n结论: 触发 OperationalError，错误码 {err_codes}")
        return 0
    print("\n结论: 未触发死锁，失败方为约束冲突（1062），非死锁")
    return 2


if __name__ == "__main__":
    sys.exit(main())
