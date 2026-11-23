from concurrent.futures import ThreadPoolExecutor, as_completed
import allure
import pytest
from common.data_faker import random_email, random_name


@allure.feature("高并发与幂等性保障")
@pytest.mark.regression
class TestUserConcurrent:

    @allure.story("并发创建同邮箱用户-唯一性与幂等拦截")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.concurrent
    def test_concurrent_create_user_same_email(self, api, db, cleaner):

        test_email = random_email()
        test_name = random_name()
        payload = {"name": test_name, "email": test_email, "status": 1}

        # 1. 注册自动回收，保障测试后环境零污染
        cleaner.register("t_user", email=test_email)

        concurrent_count = 10

        def send_request():
            return api.post("/api/users", payload)

        # 2. 线程池并发触发 10 个相同请求
        responses = []
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            # submit: 秒发号牌，任务推入线程池队列
            futures = [executor.submit(send_request) for _ in range(concurrent_count)]
            # as_completed: 哪个线程先完成就先产出结果
            for future in as_completed(futures):
                responses.append(future.result())

        # 3. 统计状态码并断言
        status_codes = [resp.status_code for resp in responses]
        assert status_codes.count(500) == 0, f"并发请求导致后端崩溃报 500: {status_codes}"
        assert status_codes.count(201) == 1, f"预期仅 1 个成功(201)，实际: {status_codes.count(201)}"
        assert status_codes.count(409) == concurrent_count - 1, (
            f"预期其余 {concurrent_count - 1} 个请求被拦截(409)，实际有 {status_codes.count(409)} 个"
        )

        # 4. 底层数据库核验：物理表里必须严格只有 1 条记录
        rows = db.query_all("SELECT id, email FROM t_user WHERE email=%s", (test_email,))
        assert len(rows) == 1, f"数据库实际写入了 {len(rows)} 条，发生并发重复写入！"
