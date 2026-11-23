import os
import allure
import pytest
from common.yaml_util import read_yaml, get_test_cases
from common.assert_util import AssertUtil
from common.schemas import (
    USER_DETAIL_SCHEMA,
    USER_LIST_SCHEMA,
    USER_CREATE_SCHEMA,
    USER_UPDATE_SCHEMA,
    USER_DELETE_SCHEMA,
    ERROR_RESPONSE_SCHEMA
)

YAML_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "user_data.yaml"
)
YAML = read_yaml(YAML_PATH)


@allure.feature("用户管理")
@pytest.mark.regression
class TestUserApi:
    @allure.story("查询用户列表")
    @pytest.mark.smoke
    # 针对性稳定性容错：针对配置了严苛 SLA 响应耗时（<=0.5s）的核心接口，防范 CI/CD 虚拟机构建并发时的偶发调度抖动
    @pytest.mark.flaky(reruns=2, reruns_delay=1)
    def test_get_users(self, api, db):
        resp = api.get("/api/users")
        body = resp.json()

        AssertUtil.assert_status_code(resp, 200)
        AssertUtil.assert_json_value(resp, "code", 0)
        AssertUtil.assert_response_time(resp, max_seconds=0.5)
        # 契约断言：全量校验用户列表响应体结构契约（必填字段与类型格式）
        AssertUtil.assert_schema(resp, USER_LIST_SCHEMA)

        db_rows = db.query_all("SELECT * FROM t_user")
        assert len(body["data"]) == len(db_rows)

    CREATE_CASES, CREATE_IDS = get_test_cases(YAML, "create_user_data")

    @allure.story("创建用户-数据驱动")
    @pytest.mark.parametrize("case", CREATE_CASES, ids=CREATE_IDS)
    def test_create_users_batch(self, api, db, cleaner, case):
        allure.dynamic.title(case["case_name"])
        payload = case["payload"]
        resp = api.post("/api/users", payload)
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_json_value(resp, "code", 0)
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        if case["expect_code"] == 201:
            AssertUtil.assert_schema(resp, USER_CREATE_SCHEMA)

        # 注册自动清理：无论后续断言是否通过，用例结束后精准删除本次创建的用户
        cleaner.register("t_user", email=payload["email"])

        row = db.query_one(
            "SELECT * FROM t_user WHERE email=%s",
            (payload["email"],)
        )
        assert row is not None
        assert row["name"] == payload["name"]

        # status 未传时后端默认设置为 1
        expected_status = (
            payload.get("status") if payload.get("status") is not None else 1
        )
        assert row["status"] == expected_status

    UPDATE_CASES, UPDATE_IDS = get_test_cases(YAML, "update_user_data")

    @allure.story("更新用户-数据驱动")
    @pytest.mark.parametrize("case", UPDATE_CASES, ids=UPDATE_IDS)
    def test_update_users_batch(self, api, db, create_user, case):
        allure.dynamic.title(case["case_name"])

        if case["need_setup"]:
            uid = create_user()
        else:
            uid = case["user_id"]

        resp = api.put(f"/api/users/{uid}", case["payload"])
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        expected_body_code = (
            0 if case["expect_code"] == 200 else case["expect_code"]
        )
        AssertUtil.assert_json_value(resp, "code", expected_body_code)

        if case["expect_code"] == 200:
            AssertUtil.assert_schema(resp, USER_UPDATE_SCHEMA)
            row = db.query_one("SELECT * FROM t_user WHERE id=%s", (uid,))
            for key, value in case["payload"].items():
                assert row[key] == value

    DELETE_CASES, DELETE_IDS = get_test_cases(YAML, "delete_user_data")

    @allure.story("删除用户-数据驱动")
    @pytest.mark.parametrize("case", DELETE_CASES, ids=DELETE_IDS)
    def test_delete_users_batch(self, api, db, create_user, case):
        allure.dynamic.title(case["case_name"])

        if case["need_setup"]:
            uid = create_user()
        else:
            uid = case["user_id"]

        resp = api.delete(f"/api/users/{uid}")
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        expected_body_code = (
            0 if case["expect_code"] == 200 else case["expect_code"]
        )
        AssertUtil.assert_json_value(resp, "code", expected_body_code)

        if case["expect_code"] == 200:
            AssertUtil.assert_schema(resp, USER_DELETE_SCHEMA)
            # 激活 DbClient.exists 封装方法进行真实数据库断言，杜绝死代码
            assert not db.exists("t_user", id=uid), f"用户未被物理删除，仍存在于数据库中: id={uid}"

    GET_CASES, GET_IDS = get_test_cases(YAML, "get_user_data")

    @allure.story("查询单个用户-数据驱动")
    @pytest.mark.parametrize("case", GET_CASES, ids=GET_IDS)
    def test_get_user_by_id_batch(self, api, db, case):
        allure.dynamic.title(case["case_name"])

        resp = api.get(f"/api/users/{case['user_id']}")
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        # expect_json=false 的用例由路由层返回 HTML，没有 JSON 响应体，跳过 code 断言
        if case.get("expect_json", True):
            expected_body_code = (
                0 if case["expect_code"] == 200 else case["expect_code"]
            )
            AssertUtil.assert_json_value(resp, "code", expected_body_code)

        if case["expect_code"] == 200:
            # 契约断言：全量校验用户详情响应体结构契约（id/name/email/status类型强校验）
            AssertUtil.assert_schema(resp, USER_DETAIL_SCHEMA)
            AssertUtil.assert_json_value(resp, "data.name", case["expect_name"])
            AssertUtil.assert_json_value(resp, "data.email", case["expect_email"])
            AssertUtil.assert_json_value(resp, "data.status", case["expect_status"])
        elif case.get("expect_json", True):
            # 错误契约断言：404 等业务错误必须符合全局统一异常响应结构
            AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)
