import time
import random
from faker import Faker

# 初始化中文 Faker 实例
fake = Faker(locale="zh_CN")


def random_name():
    """生成随机中文姓名，例如：李建国、赵晓雪"""
    return fake.name()


def random_email():
    """生成带有唯一时间戳的测试邮箱，彻底避免数据库唯一索引冲突"""
    # 格式示例：test_847291@autotest.com
    timestamp_suffix = int(time.time() * 1000) % 1000000
    random_str = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=3))
    return f"user_{timestamp_suffix}_{random_str}@autotest.com"


def random_phone():
    """生成 11 位符合规则的中国大陆手机号（为未来用户模块扩展手机号登录/绑定预留）"""
    return fake.phone_number()


# 供动态占位符解析调用的函数映射字典
DYNAMIC_FUNCTIONS = {
    "random_name": random_name,
    "random_email": random_email,
    "random_phone": random_phone,
}
