import os

CONFIG = {
    "dev": {
        "base_url": "http://127.0.0.1:5000",
        "timeout": 5,
        "db": {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "database": "my_user_api",
            "charset": "utf8mb4",
        }
    },
    "test": {
        # 测试环境（敏感信息从环境变量读取，防止密码与公网地址硬编码泄露）
        "base_url": os.getenv("TEST_BASE_URL", "http://test-api.example.com:5000"),
        "timeout": 10,
        "db": {
            "host": os.getenv("TEST_DB_HOST", "test-db.example.com"),
            "port": int(os.getenv("TEST_DB_PORT", "3306")),
            "user": os.getenv("TEST_DB_USER", "test_user"),
            "password": os.getenv("TEST_DB_PASSWORD", "your_password"),
            "database": os.getenv("TEST_DB_NAME", "my_user_api"),
            "charset": "utf8mb4",
        }
    },
}

# 优先读取系统环境变量 TEST_ENV，未设置时默认使用 dev 环境
ENV = os.getenv("TEST_ENV", "dev")

# 防御性校验：如果传入了不支持的环境名称，主动报错并列出可用环境
if ENV not in CONFIG:
    raise ValueError(f"未知环境配置: [{ENV}]！目前支持的环境有: {list(CONFIG.keys())}")


def get_config(key=None):
    env_config = CONFIG[ENV]
    if key:
        return env_config[key]
    return env_config


def get_db_config():
    return CONFIG[ENV]["db"]
