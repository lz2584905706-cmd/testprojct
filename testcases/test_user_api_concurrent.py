from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import allure
import pymysql
import pytest
import requests
from common.data_faker import random_email, random_name
from common.assert_util import AssertUtil
from common.schemas import (
    LOGIN_SUCCESS_SCHEMA,
    ERROR_RESPONSE_SCHEMA,
    USER_CREATE_SCHEMA,
    USER_UPDATE_SCHEMA,
    USER_DELETE_SCHEMA,
    USER_DETAIL_SCHEMA,
)
from config.config import get_config, get_db_config


def attach_concurrency_summary(test_name, responses):
    """
    并发可观测性增强：格式化输出并发所有线程的请求序号、状态码、耗时与响应载荷，
    自动挂载至 Allure 附件，实现排查故障时的秒级精准溯源。
    """
    lines = [
        f"=== 并发测试可观测性明细: {test_name} ===",
        f"总并发请求数: {len(responses)}",
        "-" * 80,
        f"{'序号':<6}{'状态码':<10}{'耗时(ms)':<14}{'响应体摘要'}",
        "-" * 80,
    ]
    for idx, resp in enumerate(responses, start=1):
        elapsed_ms = f"{resp.elapsed.total_seconds() * 1000:.1f}ms"
        body_preview = resp.text.replace("\n", "").strip()[:80]
        lines.append(f"{idx:<6}{resp.status_code:<10}{elapsed_ms:<14}{body_preview}")
    lines.append("-" * 80)
    summary_text = "\n".join(lines)
    allure.attach(
        summary_text,
        name=f"并发观测明细_{test_name}",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.feature("高并发与唯一性保障")
@pytest.mark.regression
class TestUserConcurrent:

    @allure.story("并发创建同邮箱用户-唯一约束冲突拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.concurrent
    def test_concurrent_create_user_same_email(self, api, db, cleaner):
        test_email = random_email()
        test_name = random_name()
        payload = {"name": test_name, "email": test_email, "status": 1}

        cleaner.register("t_user", email=test_email)
        concurrent_count = 10

        def send_request():
            return api.post("/api/users", payload)

        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_request) for _ in range(concurrent_count)]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发创建同邮箱", responses)

        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, f"并发请求导致后端崩溃报 500: {status_codes}"
        assert status_codes.count(201) == 1, f"预期仅 1 个成功(201)，实际: {status_codes.count(201)}"
        assert status_codes.count(409) == concurrent_count - 1, (
            f"预期其余 {concurrent_count - 1} 个请求被拦截(409)，实际有 {status_codes.count(409)} 个"
        )

        # 深度内容断言 1：成功创建的 201 响应体契约与自增主键合法性校验（防数据串号）
        resp_201 = next(r for r in responses if r.status_code == 201)
        AssertUtil.assert_schema(resp_201, USER_CREATE_SCHEMA)
        AssertUtil.assert_json_value(resp_201, "code", 0)
        created_id = resp_201.json()["data"]["id"]
        assert created_id > 0, f"创建用户返回的自增主键非法: {created_id}"

        # 深度内容断言 2：被拦截的 9 个 409 响应体错误契约与精准提示语校验（可观测性：带请求序号定位）
        for idx, resp_409 in enumerate([r for r in responses if r.status_code == 409], start=1):
            AssertUtil.assert_schema(resp_409, ERROR_RESPONSE_SCHEMA)
            AssertUtil.assert_json_value(resp_409, "code", 409)
            # 严格等值断言：坚持语义正确性，验证唯一约束真实拦截，杜绝模糊断言与假报错
            AssertUtil.assert_json_value(resp_409, "msg", "邮箱已被占用")

        # 深度内容断言 3：数据库物理层强一致性校验（校验落库ID与响应体返回一致）
        rows = db.query_all("SELECT id, name, email FROM t_user WHERE email=%s", (test_email,))
        assert len(rows) == 1, f"数据库实际写入了 {len(rows)} 条，发生并发重复写入！"
        assert rows[0]["id"] == created_id, f"数据库落库ID({rows[0]['id']})与接口响应ID({created_id})不一致！"
        assert rows[0]["name"] == test_name, f"落库姓名异常: {rows[0]['name']}"

    @allure.story("并发删除同一用户-状态跃迁与首发命中拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.concurrent
    def test_concurrent_delete_same_user(self, api, db, create_user):
        """
        场景：10 个线程在同一时刻对同一个用户 ID 发起删除请求。
        预期：
        1. 有且仅有 1 个请求删除成功（HTTP 200）；
        2. 其余 9 个请求因资源已被删除而精准返回 HTTP 404；
        3. 绝不能出现 500 异常；
        4. 数据库物理查询该用户已不存在。
        """
        uid = create_user()
        concurrent_count = 10

        def send_delete():
            return api.delete(f"/api/users/{uid}")

        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_delete) for _ in range(concurrent_count)]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发删除同一用户", responses)

        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, f"并发删除导致后端崩溃报 500: {status_codes}"
        assert status_codes.count(200) == 1, f"预期仅 1 个删除成功(200)，实际: {status_codes.count(200)}"
        assert status_codes.count(404) == concurrent_count - 1, (
            f"预期其余 {concurrent_count - 1} 个请求被拦截为 404，实际有 {status_codes.count(404)} 个"
        )

        # 深度内容断言 1：成功删除的 200 响应体契约与业务码校验
        resp_200 = next(r for r in responses if r.status_code == 200)
        AssertUtil.assert_schema(resp_200, USER_DELETE_SCHEMA)
        AssertUtil.assert_json_value(resp_200, "code", 0)

        # 深度内容断言 2：被拦截的 9 个 404 响应体错误契约与精准提示语校验（可观测性：带序号精准定位）
        for idx, resp_404 in enumerate([r for r in responses if r.status_code == 404], start=1):
            AssertUtil.assert_schema(resp_404, ERROR_RESPONSE_SCHEMA)
            AssertUtil.assert_json_value(resp_404, "code", 404)
            assert resp_404.json().get("msg") == "用户不存在", (
                f"[第 {idx} 个 404 响应] 提示语不符预期: {resp_404.text}"
            )

        # 深度内容断言 3：数据库物理层面确认彻底销毁
        assert not db.exists("t_user", id=uid), f"用户 ID {uid} 物理删除失败，数据库仍然存在记录！"

    @allure.story("并发高频登录-鉴权无死锁与连接池稳定性")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.concurrent
    def test_concurrent_login(self, api):
        """
        场景：10 个线程同时发起管理员登录请求。
        预期：
        1. 10 个请求全部成功返回 200；
        2. 每个请求都能成功换取有效 Token；
        3. 验证鉴权服务在高并发下无死锁阻塞、连接池不耗尽。
        """
        base_url = get_config("base_url")
        timeout = get_config("timeout")
        login_payload = {"username": "admin", "password": "123456"}
        concurrent_count = 10

        def send_login():
            return requests.post(f"{base_url}/api/login", json=login_payload, timeout=timeout)

        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_login) for _ in range(concurrent_count)]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发高频登录", responses)

        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, f"并发登录导致后端报 500: {status_codes}"
        assert status_codes.count(200) == concurrent_count, (
            f"预期 10 个登录全部成功(200)，实际: {status_codes.count(200)}"
        )
        # 深度内容断言：10 个线程返回的响应体契约与 Token 精准内容校验（带序号）
        for idx, resp in enumerate(responses, start=1):
            AssertUtil.assert_status_code(resp, 200)
            AssertUtil.assert_json_value(resp, "code", 0)
            AssertUtil.assert_schema(resp, LOGIN_SUCCESS_SCHEMA)
            assert resp.json().get("data", {}).get("token") == "test_token_123456", (
                f"[第 {idx} 个登录响应] Token 内容缺失或错误: {resp.text}"
            )

    @allure.story("并发更新同一用户-行锁串行化防死锁")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.concurrent
    def test_concurrent_update_same_user(self, api, db, create_user):
        """
        场景：10 个线程同时向同一用户更新不同的名称。
        预期：
        1. 数据库底层行锁保证更新串行化执行，全部返回 200，绝无死锁 500；
        2. 最终数据库落库的名称必定是其中一个工作线程提交的值，符合最终一致性。
        """
        uid = create_user()
        concurrent_count = 10

        def send_update(worker_idx):
            update_name = f"worker_update_{worker_idx}"
            resp = api.put(f"/api/users/{uid}", {"name": update_name})
            return resp, update_name

        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_update, i) for i in range(concurrent_count)]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发更新同一用户", [r[0] for r in responses])

        status_codes = [r[0].status_code for r in responses]
        assert status_codes.count(500) == 0, f"并发更新触发数据库死锁报 500: {status_codes}"
        assert status_codes.count(200) == concurrent_count, (
            f"预期 10 个更新全部成功(200)，实际: {status_codes.count(200)}"
        )
        # 深度内容断言 1：每个更新请求响应体均符合契约规范且 code=0（带序号）
        for idx, (resp, _) in enumerate(responses, start=1):
            AssertUtil.assert_schema(resp, USER_UPDATE_SCHEMA)
            AssertUtil.assert_json_value(resp, "code", 0)

        # 深度内容断言 2：数据库落库数据符合最终一致性，且必定是 10 个线程之一提交的值
        row = db.query_one("SELECT name FROM t_user WHERE id=%s", (uid,))
        assert row is not None
        assert row["name"].startswith("worker_update_"), f"数据库最终名称不符合预期: {row['name']}"
        submitted_names = [name for _, name in responses]
        assert row["name"] in submitted_names, "数据库落库值发生幽灵写入，不在任何并发线程参数中！"

    @allure.story("并发读风暴-连接池复用与SLA耗时监控")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.concurrent
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_concurrent_read_storm(self, api, db, create_user):
        """
        场景：10 个线程在瞬间同时读取同一个热点用户详情（读风暴）。
        预期：
        1. 10 个请求全部返回 200 且数据完全一致；
        2. 验证高频并发读取未导致数据库连接池被击穿；
        3. 平均响应时间满足 SLA 要求（<=1.2s），单个请求不超过 2.5s。
        """
        uid = create_user()
        target_user = db.query_one("SELECT * FROM t_user WHERE id=%s", (uid,))
        concurrent_count = 10

        def send_get():
            return api.get(f"/api/users/{uid}")

        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(send_get) for _ in range(concurrent_count)]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发读风暴", responses)

        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, f"读风暴导致连接池耗尽报 500: {status_codes}"
        assert status_codes.count(200) == concurrent_count, (
            f"预期 10 个读请求全部成功(200)，实际: {status_codes.count(200)}"
        )
        # 工业级 SLA 双重校验：平均耗时 + 单请求上限
        avg_elapsed = sum(r.elapsed.total_seconds() for r in responses) / len(responses)
        assert avg_elapsed <= 1.2, f"并发读平均响应耗时超标: {avg_elapsed:.3f}s"
        for idx, resp in enumerate(responses, start=1):
            assert resp.elapsed.total_seconds() <= 2.5, (
                f"[第 {idx} 个并发读请求] 响应耗时超标: {resp.elapsed.total_seconds()}s"
            )
            # 深度内容断言：10 个并发线程返回的响应体契约与数据 100% 强一致，无脏读/空读
            AssertUtil.assert_schema(resp, USER_DETAIL_SCHEMA)
            AssertUtil.assert_json_value(resp, "code", 0)
            AssertUtil.assert_json_value(resp, "data.id", uid)
            AssertUtil.assert_json_value(resp, "data.name", target_user["name"])
            AssertUtil.assert_json_value(resp, "data.email", target_user["email"])
            AssertUtil.assert_json_value(resp, "data.status", target_user["status"])

    @allure.story("并发更新不同用户至同一邮箱-唯一约束在 UPDATE 路径的竞态拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.concurrent
    def test_concurrent_update_to_same_email(self, api, db, create_user, cleaner):
        """
        场景：10 个线程同时把 10 个不同用户的邮箱改成同一个目标邮箱。
        预期：
        1. 有且仅有 1 个请求更新成功（HTTP 200）；
        2. 其余 9 个请求因唯一索引冲突被拦截（HTTP 409）；
        3. 绝不能出现 500 异常（含 MySQL 并发死锁场景）；
        4. 数据库物理表里该目标邮箱严格只有 1 条记录。
        """
        target_email = random_email()
        cleaner.register("t_user", email=target_email)

        # 先准备 10 个互不相同的用户，各自持有独立邮箱（create_user 已自动登记回收）
        uids = [create_user() for _ in range(10)]

        def send_update(uid):
            return api.put(f"/api/users/{uid}", {"email": target_email})

        responses = []
        with ThreadPoolExecutor(max_workers=len(uids)) as executor:
            futures = [executor.submit(send_update, uid) for uid in uids]
            for future in as_completed(futures):
                responses.append(future.result())

        attach_concurrency_summary("并发更新至同一邮箱", responses)

        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, (
            f"并发更新邮箱导致后端 500（可能为 MySQL 死锁 1213 未处理）: {status_codes}"
        )
        assert status_codes.count(200) == 1, (
            f"预期仅 1 个更新成功(200)，实际: {status_codes.count(200)}"
        )
        assert status_codes.count(409) == len(uids) - 1, (
            f"预期其余 {len(uids) - 1} 个请求被唯一约束拦截(409)，实际有 {status_codes.count(409)} 个"
        )

        # 深度内容断言 1：唯一的 200 响应符合更新契约与业务码
        resp_200 = next(r for r in responses if r.status_code == 200)
        AssertUtil.assert_schema(resp_200, USER_UPDATE_SCHEMA)
        AssertUtil.assert_json_value(resp_200, "code", 0)

        # 深度内容断言 2：被拦截的 9 个 409 响应体符合错误契约与精准提示语（严格等值断言，验证唯一索引拦截）
        for idx, resp_409 in enumerate([r for r in responses if r.status_code == 409], start=1):
            AssertUtil.assert_schema(resp_409, ERROR_RESPONSE_SCHEMA)
            AssertUtil.assert_json_value(resp_409, "code", 409)
            # 严格等值断言：坚决杜绝为了测试通过去磨钝断言，验证唯一性业务拦截
            AssertUtil.assert_json_value(resp_409, "msg", "邮箱已被占用")

        rows = db.query_all("SELECT id, email FROM t_user WHERE email=%s", (target_email,))
        assert len(rows) == 1, f"目标邮箱在库中出现 {len(rows)} 条记录，唯一约束失效！"

    @allure.story("并发竞态-更新途中目标用户被删除")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.concurrent
    def test_update_blocked_then_user_deleted(self, api, db, create_user):
        """
        场景：更新请求已完成「读取当前用户」，随后卡在行锁上等待；
             等待期间另一个事务把该用户删除并提交。
        预期：UPDATE 影响 0 行，接口必须如实返回 404（资源已不存在），
             绝不能谎报「更新成功」，否则调用方会误以为数据还在。

        放大竞态窗口的办法：人工事务先锁住目标行。
        后端那条普通 SELECT 是快照读，不受锁影响，能顺利读到用户；
        真正卡住的是后面的 UPDATE，它要申请被我们持有的行锁。
        """
        uid = create_user()
        lock_conn = pymysql.connect(**get_db_config(), autocommit=False)
        try:
            with lock_conn.cursor() as cur:
                cur.execute("SELECT id FROM t_user WHERE id=%s FOR UPDATE", (uid,))

            result = {}

            def send_update():
                result["resp"] = api.put(f"/api/users/{uid}", {"name": "updated_but_deleted"})

            worker = threading.Thread(target=send_update)
            worker.start()

            # 给后端留出「完成 SELECT、进入 UPDATE 等锁」的时间
            time.sleep(0.3)

            # 同一事务内删除该用户并提交，让后端的 UPDATE 醒来后无行可改
            with lock_conn.cursor() as cur:
                cur.execute("DELETE FROM t_user WHERE id=%s", (uid,))
            lock_conn.commit()

            worker.join(timeout=15)
            resp = result.get("resp")
            assert resp is not None, "更新请求未在规定时间内返回"
            assert resp.status_code == 404, (
                f"目标用户已被并发删除，更新应返回 404，实际 {resp.status_code}: {resp.text}"
            )
            AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)
        finally:
            lock_conn.close()
