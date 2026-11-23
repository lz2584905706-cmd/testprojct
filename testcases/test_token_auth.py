import requests
import allure
import pytest
from config.config import get_config
from common.assert_util import AssertUtil
from common.schemas import LOGIN_SUCCESS_SCHEMA, ERROR_RESPONSE_SCHEMA

BASE_URL = get_config('base_url')
TIMEOUT = get_config('timeout')


@allure.feature("用户管理-鉴权")
@pytest.mark.security
class TestTokenAuth:

    @allure.story("未登录访问")
    def test_no_token(self):
        """不带 token 请求用户列表，应返回 401 并符合错误响应契约"""
        resp = requests.get(f"{BASE_URL}/api/users", timeout=TIMEOUT)
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        AssertUtil.assert_json_value(resp, "code", 401)
        AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)

    @allure.story("未登录访问")
    def test_wrong_token(self):
        """带错误 token 请求，应返回 401 并符合错误响应契约"""
        resp = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": "Bearer wrong_token_123"},
            timeout=TIMEOUT
        )
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        AssertUtil.assert_json_value(resp, "code", 401)
        AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)

    @allure.story("登录")
    def test_login_wrong_password(self):
        """密码错误登录，应返回 401 并符合错误响应契约"""
        resp = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "wrong"},
            timeout=TIMEOUT
        )
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        AssertUtil.assert_json_value(resp, "code", 401)
        AssertUtil.assert_schema(resp, ERROR_RESPONSE_SCHEMA)

    @allure.story("登录")
    @pytest.mark.smoke
    def test_login_success(self):
        """正确登录，应返回 200 且符合 Token 颁发契约"""
        resp = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "123456"},
            timeout=TIMEOUT
        )
        AssertUtil.assert_status_code(resp, 200)
        AssertUtil.assert_response_time(resp, max_seconds=1.0)
        AssertUtil.assert_json_value(resp, "code", 0)
        AssertUtil.assert_schema(resp, LOGIN_SUCCESS_SCHEMA)
