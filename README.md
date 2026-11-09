# 用户管理接口自动化测试项目

基于 Flask + Pytest + Allure 搭建的接口自动化测试教学项目，覆盖用户管理模块的增删改查、反向场景与 Token 鉴权。

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Flask + MySQL |
| 测试框架 | Pytest |
| 数据驱动 | YAML |
| 报告 | Allure |
| 日志 | logging（控制台 + 文件） |
| HTTP 请求 | Requests |
| 数据库连接 | PyMySQL |

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
pip install -r requirements.txt
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

- **数据驱动**：测试数据与代码分离，YAML 维护，新增用例只需加数据
- **双重断言**：既校验接口响应，又查数据库验证数据落库
- **Fixtures 前后置**：每个用例前自动清表重置数据，用例间互不影响
- **Token 鉴权**：自动登录获取 Token，后续请求自动携带
- **多环境配置**：切换 dev/test 环境只需改一行配置
- **日志记录**：请求/响应自动写入日志文件，方便排查
- **Allure 报告**：按 feature/story 分层展示，失败用例自动附带响应详情
- **Fiddler 代理**：DEBUG_PROXY 开关一键切换抓包模式

## 测试覆盖

| 模块 | 覆盖场景 |
|---|---|
| 查询用户列表 | 接口返回条数与数据库一致 |
| 查询单个用户 | 正常查询、用户不存在(404) |
| 创建用户 | 正常创建(含中文/长名/禁用状态)、缺字段(400)、空字符串(400)、重复邮箱(409)、不传status默认值 |
| 更新用户 | 只改name、只改status、同时改多个字段、用户不存在(404) |
| 删除用户 | 正常删除、用户不存在(404) |
| 鉴权 | 无Token(401)、错误Token(401)、密码错误(401)、正确登录返回Token |
