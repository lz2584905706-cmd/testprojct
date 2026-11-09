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
        "base_url": "http://shturl.cc/Y3:5000",
        "timeout": 10,
        "db": {
            "host": "shturl.cc/Y3",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "database": "my_user_api",
            "charset": "utf8mb4",
        }
    },
}

ENV = "dev"


def get_config(key=None):
    env_config = CONFIG[ENV]
    if key:
        return env_config[key]
    return env_config


def get_db_config():
    return CONFIG[ENV]["db"]