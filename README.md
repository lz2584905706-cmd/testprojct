# 用户管理接口自动化测试项目

[![CI Pipeline](https://github.com/lz2584905706-cmd/testprojct/actions/workflows/test_pipeline.yml/badge.svg)](https://github.com/lz2584905706-cmd/testprojct/actions/workflows/test_pipeline.yml)

基于 Flask + Pytest + Allure 搭建的接口自动化测试教学项目，覆盖用户管理模块的增删改查、反向场景与 Token 鉴权。

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Flask + MySQL 8.0 |
| 测试框架 | Pytest 9.2.0 |
| 数据驱动 | YAML + Faker 动态造数引擎 |
| 持续集成 | GitHub Actions CI/CD 流水线 |
| 容器化 | Docker + Docker Compose 编排 |
| 质量监控 | SLA 响应耗时监控 + Flaky 局部重试 |
| 报告与日志 | Allure 2.16 + 日志记录（控制台/文件） |
| 网络与数据库 | Requests + PyMySQL |

## 项目结构

```
xiangmu3/
├── backend/
│   └── app.py              # Flask 后端（5个用户接口 + 登录接口 + Token鉴权）
├── common/
│   ├── api_client.py       # HTTP 请求封装（自动登录、异常处理、Fiddler代理）
│   ├── db_client.py        # 数据库操作封装
│   ├── yaml_util.py        # YAML 数据读取
│   ├── logger.py           # 日志模块
│   └── assert_util.py      # 断言封装（失败自动记录响应到Allure）
├── config/
│   └── config.py           # 多环境配置（dev/test）
├── data/
│   └── user_data.yaml      # 测试数据（数据驱动）
├── testcases/
│   ├── test_user_api.py           # 正向用例（CRUD数据驱动）
│   ├── test_user_api_negative.py  # 反向用例（缺字段/重复邮箱）
│   └── test_token_auth.py         # 鉴权用例（401/登录）
├── sql/
│   └── init.sql            # 建表语句
├── conftest.py             # Pytest fixture（清表、api/db实例、造数据）
├── pytest.ini              # Pytest 配置
├── requirements.txt        # 依赖清单
└── .gitignore
```

## 环境准备

1. 安装 Python 3.10+
2. 启动 MySQL，创建数据库 `my_user_api`，执行 `sql/init.sql` 建表
3. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
# 测试开发全量依赖安装
pip install -r requirements-dev.txt
```

## 启动后端

```bash
python backend/app.py
```

后端运行在 http://127.0.0.1:5000

## 执行测试

```bash
# 跑全部用例
pytest

# 生成 Allure 报告
allure serve reports/allure
```

## 功能特性

- **数据驱动**：测试数据与代码解耦，YAML 维护，支持 `${random_email()}` 等动态占位符
- **动态造数引擎**：集成 Faker 并采用内存递归安全替换，彻底避免唯一键与并发数据冲突
- **双重断言**：既校验接口响应状态码与业务 code，又查数据库验证数据物理落库
- **数据回收站 (Teardown)**：引入 `cleaner` Fixture 精准回收测试临时脏数据，0 数据污染，环境高度幂等
- **SLA 耗时监控**：核心正向接口内置响应耗时 SLA 断言，自动拦截慢接口
- **契约测试校验**：引入 `JsonSchema` 严格校验响应体字段、类型与必填约束，超越传统单字段断言
- **高并发与幂等保障**：线程池并发模拟高频重复请求，严苛验证数据库唯一索引与竞态拦截
- **分层测试**：打标 `smoke`、`regression`、`security`、`concurrent`，支持秒级筛选
- **CI/CD 持续集成**：GitHub Actions 云端自动化拉起 MySQL、执行健康检查轮询并产出 Allure 报告
- **Docker 容器化**：提供精简 `Dockerfile` 与多容器编排 `docker-compose.yml`，规避宿主机端口冲突

## 测试覆盖

共 52 条用例（含 1 条 Faker 动态造数用例、1 条并发幂等测试用例），单次全量执行约 8~12 秒，全绿通过。

| 模块 | 覆盖场景 |
|---|---|
| 查询用户列表 | 接口返回条数与数据库一致、契约结构校验 |
| 查询单个用户 | 正常查询（含契约校验）、用户不存在(404)、id=0(404)、负数id(路由层404) |
| 创建用户 | 正常创建(含中文/长名/50字符边界/禁用状态/Faker动态造数)、缺字段(400)、空字符串(400)、null字段(400)、重复邮箱(409)、name超长(400)、email超长(400)、非法邮箱格式(400)、status非法值(400)、不传status默认值 |
| 更新用户 | 只改name、只改email、只改status、同时改多个字段、用户不存在(404)、改成已存在邮箱(409)、name为空(400)、name超长(400)、非法邮箱格式(400)、status非法值(400) |
| 删除用户 | 正常删除、用户不存在(404)、id=0(404) |
| 高并发与幂等 | 10 线程并发创建同邮箱用户：有且仅有 1 个返回 201、9 个返回 409、0 崩溃(500)、底层落库严格等于 1 条 |
| 鉴权 | 无Token(401)、错误Token(401)、密码错误(401)、正确登录返回Token |
