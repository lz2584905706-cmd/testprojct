import sys
import uuid
from pathlib import Path
from locust import HttpUser, between, events, task

# 确保从任意路径启动 locust 命令时，均能正常导入项目根目录模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.data_faker import random_name  # noqa: E402
from common.db_client import DbClient  # noqa: E402
from config.config import get_config  # noqa: E402

PERF_EMAIL_PREFIX = "perf_"
PERF_EMAIL_DOMAIN = "autotest.com"


def build_perf_email():
    return f"{PERF_EMAIL_PREFIX}{uuid.uuid4().hex[:12]}@{PERF_EMAIL_DOMAIN}"


@events.test_stop.add_listener
def cleanup_perf_users(environment, **kwargs):
    """压测停止后精准清理带 perf_ 前缀的临时数据，严禁触碰 alice/bob/carol 基线。"""
    if environment.runner and environment.runner.__class__.__name__ == "WorkerRunner":
        return
    try:
        deleted = DbClient().execute(
            "DELETE FROM t_user WHERE email LIKE %s",
            (f"{PERF_EMAIL_PREFIX}%@{PERF_EMAIL_DOMAIN}",),
        )
        print(f"[Locust Teardown] 已自动清理压测新增用户 {deleted} 条，只读基线数据完好保留。")
    except Exception as exc:
        print(f"[Locust Teardown] 自动清理压测数据失败: {exc}")


class BaseUserApiLoad(HttpUser):
    """接口压测虚拟用户基类：统一管理目标地址、思考时间、Token 登录及业务级断言。"""

    abstract = True
    host = get_config("base_url")
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """每个虚拟用户启动时执行一次登录，提取有效 Token 并注入默认请求头。"""
        with self.client.post(
            "/api/login",
            json={"username": "admin", "password": "123456"},
            catch_response=True,
            name="/api/login [POST]",
        ) as resp:
            payload = self._verify_json_response(resp, expected_status=200, mark_success=False)
            if payload is None:
                return
            token = (payload.get("data") or {}).get("token")
            if not token:
                resp.failure("登录响应缺少 data.token 字段")
                return
            resp.success()
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @staticmethod
    def _verify_json_response(resp, expected_status, mark_success=True):
        """校验 HTTP 状态码与业务 code==0，防止 HTTP 200 下返回业务异常的假成功。"""
        if resp.status_code != expected_status:
            resp.failure(f"期望 HTTP {expected_status}，实际为 {resp.status_code}")
            return None
        try:
            payload = resp.json()
        except ValueError:
            resp.failure("响应体不是合法 JSON 格式")
            return None
        if not isinstance(payload, dict) or payload.get("code") != 0:
            code = payload.get("code") if isinstance(payload, dict) else "N/A"
            msg = payload.get("msg") if isinstance(payload, dict) else str(payload)
            resp.failure(f"业务返回码异常: code={code}, msg={msg}")
            return None
        if mark_success:
            resp.success()
        return payload

    def _do_list_users(self):
        """查询用户列表，要求 HTTP 200 且业务 code == 0。"""
        with self.client.get(
            "/api/users",
            catch_response=True,
            name="/api/users [GET]",
        ) as resp:
            self._verify_json_response(resp, expected_status=200)

    def _do_create_user(self):
        """创建随机唯一用户，要求 HTTP 201 且业务 code == 0。"""
        body = {
            "name": random_name(),
            "email": build_perf_email(),
            "status": 1,
        }
        with self.client.post(
            "/api/users",
            json=body,
            catch_response=True,
            name="/api/users [POST]",
        ) as resp:
            self._verify_json_response(resp, expected_status=201)


class ReadOnlyUser(BaseUserApiLoad):
    """纯读基准用户模型：专注探测 GET /api/users 查询接口吞吐上限。"""

    @task
    def list_users(self):
        self._do_list_users()


class MixedLoadUser(BaseUserApiLoad):
    """读写混合业务模型：模拟 80% 高频查询 + 20% 新增写入的真实流量比例。"""

    @task(4)
    def list_users(self):
        self._do_list_users()

    @task(1)
    def create_user(self):
        self._do_create_user()
