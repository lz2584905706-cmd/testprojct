from common.logger import get_logger
import allure

logger =  get_logger()

class AssertUtil:
    @staticmethod
    def _safe_body(resp):
        try:
            return resp.json()
        except Exception:
            return resp.text

    @staticmethod
    def assert_status_code(resp, expect_code):
        try:
            assert resp.status_code == expect_code,f"状态码校验失败！预期:{expect_code},实际:{resp.status_code}"
        except AssertionError as e:
            body = AssertUtil._safe_body(resp)
            logger.error(f"响应返回内容{body}")
            allure.attach(f"状态码校验失败\n预期:{expect_code}\n实际:{resp.status_code}\n完整响应:{body}",
                name="断言失败详情", attachment_type=allure.attachment_type.TEXT)
            raise e

    @staticmethod
    def assert_json_value(resp, json_key, expect_value):
        try:
            json_data = resp.json()
            keys = json_key.split(".")
            actual = json_data
            for k in keys:
                actual = actual.get(k)
                if actual is None:
                    break
            assert actual == expect_value,f"字段{json_key}校验失败！预期:{expect_value},实际:{actual}"
        except AssertionError as e:
            body = AssertUtil._safe_body(resp)
            logger.error(f"响应返回内容{body}")
            allure.attach(
                f"字段{json_key}校验失败\n预期:{expect_value}\n实际:{actual}\n完整响应:{body}",
                name="断言失败详情", attachment_type=allure.attachment_type.TEXT)
            raise e