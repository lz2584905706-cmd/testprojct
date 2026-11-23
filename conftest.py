import pytest
from common.api_client import ApiClient
from common.db_client import DbClient
from common.data_faker import random_name, random_email


INIT_SQL = [
    "TRUNCATE TABLE t_user",
    "INSERT INTO t_user (name, email, status) VALUES "
    "('alice','alice@test.com',1),('bob','bob@test.com',1),('carol','carol@test.com',0)"
]


@pytest.fixture(scope='session', autouse=True)
def init_test_db():
    """整个测试套件启动时，初始化一次基础数据基线（Session 级别，避免每条用例 DDL 清表）"""
    db = DbClient()
    for sql in INIT_SQL:
        db.execute(sql)
    yield


class DataCleaner:
    """测试数据回收站，负责记录用例中创建的数据并在用例结束后精准删除，保持测试隔离与幂等"""
    def __init__(self, db):
        self.db = db
        self.records = []

    def register(self, table, **conditions):
        """登记待清理的数据"""
        self.records.append((table, conditions))

    def clean(self):
        """精准逆序清理，保证数据恢复"""
        for table, conditions in reversed(self.records):
            try:
                self.db.delete(table, **conditions)
            except Exception as e:
                print(f"[DataCleaner] 数据清理异常: {table} {conditions}, 错误: {e}")


@pytest.fixture(scope='function')
def cleaner(db):
    """用例级数据清理器：用例结束后自动执行 teardown 回收数据"""
    clean_tool = DataCleaner(db)
    yield clean_tool
    clean_tool.clean()


@pytest.fixture(scope='function')
def api():
    return ApiClient()


@pytest.fixture(scope='function')
def db():
    return DbClient()


@pytest.fixture
def create_user(api, cleaner):
    def _create_user(name=None, email=None, status=1):
        actual_name = name or random_name()
        actual_email = email or random_email()
        resp = api.post(
            "/api/users",
            {"name": actual_name, "email": actual_email, "status": status}
        )
        uid = resp.json()["data"]["id"]
        # 自动登记到清理回收站，用例结束后精准删除该临时用户
        cleaner.register("t_user", id=uid)
        return uid
    return _create_user
