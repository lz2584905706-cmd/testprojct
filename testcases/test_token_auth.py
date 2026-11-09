import os
import requests
import allure
from config.config import get_config

BASE_URL = get_config('base_url')
TIMEOUT = get_config('timeout')


@allure.feature("用户管理-鉴权")
class TestTokenAuth:

    @allure.story("未登录访问")
    def test_no_token(self):
        """不带 token 请求用户列表，应返回 401"""
        resp = requests.get(f"{BASE_URL}/api/users", timeout=TIMEOUT)
        assert resp.status_code == 401

    @allure.story("未登录访问")
    def test_wrong_token(self):
        """带错误 token 请求，应返回 401"""
        resp = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": "Bearer wrong_token_123"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 401

    @allure.story("登录")
    def test_login_wrong_password(self):
        """密码错误登录，应返回 401"""
        resp = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "wrong"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 401

    @allure.story("登录")
    def test_login_success(self):
        """正确登录，应返回 200 且带 token"""
        resp = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "123456"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "token" in body["data"]