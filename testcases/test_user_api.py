import os
import allure
import pytest
from common.yaml_util import read_yaml, get_test_cases
from common.assert_util import AssertUtil

YAML = read_yaml(os.path.join(os.path.dirname(__file__), "..", "data", "user_data.yaml"))

@allure.feature("用户管理")
class TestUserApi:
    @allure.story("查询用户列表")
    def test_get_users(self, api, db):
        resp = api.get("/api/users")
        body = resp.json()

        AssertUtil.assert_status_code(resp, 200)
        AssertUtil.assert_json_value(resp, "code", 0)

        db_rows = db.query_all("SELECT * FROM t_user")
        assert len(body["data"]) == len(db_rows)


    CREATE_CASES, CREATE_IDS = get_test_cases(YAML, "create_user_data")
    @allure.story("创建用户-数据驱动")
    @pytest.mark.parametrize("case", CREATE_CASES, ids=CREATE_IDS)
    def test_create_users_batch(self, api, db, case):
        allure.dynamic.title(case["case_name"])
        body = {"name": case["name"], "email": case["email"]}
        if case.get("status") is not None:
            body["status"] = case["status"]
        resp = api.post("/api/users", body)
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_json_value(resp, "code", 0)


        row = db.query_one("SELECT * FROM t_user WHERE email=%s", (case["email"],))
        assert row is not None
        assert row["name"] == case["name"]

        if case["status"] is not None:
            expected_status = case["status"]
        else:
            expected_status = 1
        assert row["status"] == expected_status

    UPDATE_CASES, UPDATE_IDS = get_test_cases(YAML, "update_user_data")
    @allure.story("更新用户-数据驱动")
    @pytest.mark.parametrize("case", UPDATE_CASES, ids=UPDATE_IDS)
    def test_update_users_batch(self, api, db, create_user, case):
        allure.dynamic.title(case["case_name"])

        if case["need_setup"]:
            uid = create_user(name="tmp", email=f"tmp_{case['case_name']}@test.com", status=1)
        else:
            uid = case["user_id"]

        resp = api.put(f"/api/users/{uid}", case["payload"])
        AssertUtil.assert_status_code(resp, case["expect_code"])

        if case["expect_code"] == 200:
            row = db.query_one("SELECT * FROM t_user WHERE id=%s", (uid,))
            for key, value in case["payload"].items():
                assert row[key] == value

    DELETE_CASES, DELETE_IDS = get_test_cases(YAML, "delete_user_data")

    @allure.story("删除用户-数据驱动")
    @pytest.mark.parametrize("case", DELETE_CASES, ids=DELETE_IDS)
    def test_delete_users_batch(self, api, db, create_user, case):
        allure.dynamic.title(case["case_name"])

        if case["need_setup"]:
            uid = create_user(name="tmp", email=f"tmp_{case['case_name']}@test.com", status=1)
        else:
            uid = case["user_id"]

        resp = api.delete(f"/api/users/{uid}")
        AssertUtil.assert_status_code(resp, case["expect_code"])

        if case["expect_code"] == 200:
            row = db.query_one("SELECT * FROM t_user WHERE id=%s", (uid,))
            assert row is None


    GET_CASES, GET_IDS = get_test_cases(YAML, "get_user_data")
    @allure.story("查询单个用户-数据驱动")
    @pytest.mark.parametrize("case", GET_CASES, ids=GET_IDS)
    def test_get_user_by_id_batch(self, api, db, case):
        allure.dynamic.title(case["case_name"])

        resp = api.get(f"/api/users/{case['user_id']}")
        AssertUtil.assert_status_code(resp, case["expect_code"])

        if case["expect_code"] == 200:
            AssertUtil.assert_json_value(resp, "data.name", case["expect_name"])
            AssertUtil.assert_json_value(resp, "data.email", case["expect_email"])
            AssertUtil.assert_json_value(resp, "data.status", case["expect_status"])
