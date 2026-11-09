import os
os.environ["PYTEST_UTF8_IDS"] = "1"
import pytest
from common.api_client import ApiClient
from common.db_client import DbClient

@pytest.fixture(scope='session')
def store():
    return {}

INIT_SQL = [
    "TRUNCATE TABLE t_user",
    "INSERT INTO t_user (name, email, status) VALUES ('alice','alice@test.com',1),('bob','bob@test.com',1),('carol','carol@test.com',0)"
]

@pytest.fixture(autouse=True)
def reset_db():
    db=DbClient()
    for sql in INIT_SQL:
        db.execute(sql)
    yield

@pytest.fixture(scope='function')
def api():
    return ApiClient()

@pytest.fixture(scope='function')
def db():
    return DbClient()

@pytest.fixture
def create_user(api):
    def _create_user(name="test_user", email="test@test.com", status=1):
        resp=api.post("/api/users", {"name": name, "email": email, "status": status})
        return resp.json()["data"]["id"]
    return _create_user