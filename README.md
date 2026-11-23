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
- **双重断言与高阶封装**：既校验接口响应状态码与业务 code，又通过 `DbClient.exists()` 严苛验证数据物理落库与物理销毁
- **数据回收站 (Teardown)**：引入 `cleaner` Fixture 精准回收测试临时脏数据，0 数据污染，环境高度幂等
- **全量 SLA 耗时监控**：正向接口、单用户查询、鉴权登录与异常参数校验全量内置响应耗时 SLA 断言，自动拦截性能退化
- **全场景契约闭环测试**：引入 `JsonSchema` 覆盖用户 CRUD、Token 登录鉴权及全局统一异常响应（400/401/404/409），彻底杜绝契约破坏
- **全工程统一断言规范**：正向、反向、鉴权用例 100% 接入 `AssertUtil`，任何断言失败均自动捕获请求与响应正文并附加至 Allure 报告
- **高并发双层深度断言**：构建涵盖增、删、改、查、鉴权等 6 大场景的高并发测试体系，不仅校验 HTTP 协议状态码分布，更穿透断言响应体业务字段、自增 ID 合法性、强一致性与 JsonSchema 契约，彻底杜绝多线程环境下的数据串号与假报错
- **分层测试**：打标 `smoke`、`regression`、`security`、`concurrent`，支持秒级筛选
- **CI/CD 持续集成**：GitHub Actions 云端 Python 3.11/3.12/3.13 矩阵并行构建，自动化拉起 MySQL、健康检查轮询并产出 Allure 单文件 HTML 报告
- **Docker 容器化**：提供精简 `Dockerfile` 与多容器编排 `docker-compose.yml`，规避宿主机端口冲突

## 测试覆盖

共 57 条用例（含 1 条 Faker 动态造数用例、6 条高并发高可用用例），单次全量执行约 15~22 秒，全绿通过。

| 模块 | 覆盖场景 |
|---|---|
| 查询用户列表 | 接口返回条数与数据库一致、契约结构校验 (GET) |
| 查询单个用户 | 正常查询（含契约校验 GET）、用户不存在(404)、id=0(404)、负数id(路由层404) |
| 创建用户 | 正常创建(含中文/长名/50字符边界/禁用状态/Faker动态造数/写契约校验 POST 201)、缺字段(400)、空字符串(400)、null字段(400)、重复邮箱(409)、name超长(400)、email超长(400)、非法邮箱格式(400)、status非法值(400)、不传status默认值 |
| 更新用户 | 只改name、只改email、只改status、同时改多个字段(含契约校验 PUT 200)、用户不存在(404)、改成已存在邮箱(409)、name为空(400)、name超长(400)、非法邮箱格式(400)、status非法值(400) |
| 删除用户 | 正常删除(含契约校验 DELETE 200)、用户不存在(404)、id=0(404) |
| 高并发与高可用 | 涵盖 6 大场景：①并发创建同邮箱(1x201+9x409)；②并发删除同用户(1x200+9x404)；③并发高频登录(10x200)；④并发更新同用户(行锁防死锁)；⑤并发读风暴(10线程SLA耗时监控)；⑥并发更新至同一邮箱(唯一约束在 UPDATE 路径同样生效，1x200+9x409) |
| 鉴权 | 无Token(401)、错误Token(401)、密码错误(401)、正确登录返回Token |
