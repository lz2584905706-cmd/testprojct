import os
import allure
import pytest
from common.yaml_util import read_yaml, get_test_cases
from common.assert_util import AssertUtil
from common.schemas import ERROR_RESPONSE_SCHEMA

YAML_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "user_data.yaml"
)
YAML = read_yaml(YAML_PATH)
NEG_CASES, NEG_IDS = get_test_cases(YAML, "create_user_negative_data")


@allure.feature("用户管理-异常场景")
@pytest.mark.regression
class TestUserApiNegative:

    @allure.story("创建用户-反向")
    @pytest.mark.parametrize("case", NEG_CASES, ids=NEG_IDS)
    def test_create_user_negative(self, api, case):
        allure.dynamic.title(case["case_name"])
        resp = api.post("/api/users", case["payload"])
        AssertUtil.assert_status_code(resp, case["expect_code"])
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        AssertUtil.assert_json_value(resp, "code", case["expect_code"])
        AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)
