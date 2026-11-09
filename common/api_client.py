import requests
from config.config import get_config
from common.logger import get_logger

logger = get_logger()


DEBUG_PROXY = False
FIDDLER_PROXY = "http://127.0.0.1:8888"#Fiddler 调试开关


class ApiClient:
    def __init__(self):
        self.base_url = get_config('base_url')
        self.timeout = get_config('timeout')
        self.headers = {"Content-Type": "application/json"}
        self._login()

        if DEBUG_PROXY:
            self.proxies = {"http": FIDDLER_PROXY, "https": FIDDLER_PROXY}
            self.verify = False
        else:
            self.proxies = None
            self.verify = True

    def _login(self):
        resp = requests.post(self.base_url + "/api/login",json={"username": "admin", "password": "123456"},timeout=self.timeout)
        token= resp.json()["data"]["token"]
        self.headers["Authorization"] = f"Bearer {token}"


    def get(self, path):
        try:
            url = self.base_url + path
            logger.info(f"GET {url}")
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"GET 请求异常 {e}")
            raise e
        return resp

    def post(self, path, body):
        try:
            url = self.base_url + path
            logger.info(f"POST {url} body={body}")
            resp = requests.post(url, json=body, headers=self.headers, timeout=self.timeout)
            logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"POST 请求异常 {e}")
            raise e
        return resp

    def put(self, path, body):
        try:
            url = self.base_url + path
            logger.info(f"PUT {url} body={body}")
            resp = requests.put(url, json=body, headers=self.headers, timeout=self.timeout)
            logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"PUT 请求异常 {e}")
            raise e
        return resp

    def delete(self, path):
        try:
            url = self.base_url + path
            logger.info(f"DELETE {url}")
            resp = requests.delete(url, headers=self.headers, timeout=self.timeout)
            logger.info(f"Response {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"DELETE 请求异常 {e}")
            raise e
        return resp