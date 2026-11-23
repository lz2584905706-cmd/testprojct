# 项目上下文档案 (PROJECT_CONTEXT.md)

## 1. 项目基本信息
- **项目名称**：user_api_test（用户管理接口自动化测试工程）
- **项目定位**：企业级高可用 RESTful 接口自动化测试框架（含 CI/CD、Docker、动态造数、数据幂等治理）
- **工作区路径**：`E:\DoubaoWork\user_api_test`（对应物理源码路径 `D:\xiangmu3`）
- **Python 版本**：Python 3.12（虚拟环境位于 `.venv/`）

## 2. 核心架构与模块分层
- `backend/app.py`：被测 Flask 后端服务（用户 CRUD 接口 + Token 登录鉴权）
- `common/api_client.py`：统一 HTTP 客户端（自动携带 Token、请求日志、异常封装）
- `common/db_client.py`：数据库客户端（参数化安全查询、`exists()` 断言、`delete()` 精准删除）
- `common/yaml_util.py`：YAML 解析引擎（结合 `DYNAMIC_FUNCTIONS` 实现内存递归动态参数化替换）
- `common/data_faker.py`：动态造数工厂（Faker 中文本土化、唯一时间戳邮箱）
- `common/assert_util.py`：断言增强工具（状态码校验、JSON 字段路径提取、SLA 耗时校验、JsonSchema 契约断言并自动关联 Allure 证据链）
- `common/schemas.py`：JsonSchema 契约模型中心（覆盖用户 CRUD、Token 登录鉴权及全局统一异常响应）
- `conftest.py`：全局与用例级 Fixture 治理（Session 级基线初始化、`cleaner` 回收站 Teardown 机制）
- `config/config.py`：多环境配置中心（支持 `TEST_ENV` 动态切换，敏感配置解耦）

## 3. 测试用例统计（共 57 条）
- **正向业务用例（34 条）**：
  - 用户查询列表、用户详情查询（全量契约与 SLA 耗时校验）
  - 批量创建用户（11 条，含 1 条 Faker 动态造数用例，响应结构契约校验）
  - 批量更新用户（11 条，响应契约校验）
  - 批量删除用户（3 条，响应契约校验与 `db.exists()` 物理落库校验）
- **反向异常用例（13 条）**：
  - 缺必填字段、空值、超长边界、非法邮箱格式、重复邮箱拦截（全量接入 SLA 耗时断言与 `ERROR_RESPONSE_SCHEMA` 错误契约校验）
- **高并发与高可用测试用例（6 条，全量实施双层深度断言）**：
  - 1. 并发创建同邮箱：10 线程验证 1x201+9x409+0x500，深度校验 201 响应体自增 ID 合法性与 409 精准提示语（"邮箱已被占用"）
  - 2. 并发删除同用户：10 线程验证 1x200+9x404+0x500，深度校验 200 删除契约与 404 错误响应（"用户不存在"），`db.exists()` 校验物理销毁
  - 3. 并发高频登录：10 线程同时发起鉴权登录，深度校验 `LOGIN_SUCCESS_SCHEMA` 契约合规与颁发 Token 精准值
  - 4. 并发更新同用户：10 线程同时更新同用户，深度校验各响应体契约，验证 MySQL 行锁串行化防死锁与最终一致性（杜绝幽灵写入）
  - 5. 并发读风暴：10 线程同时高频读取同一热点数据，深度校验 10 线程返回内容 100% 强一致（无脏读空读）与 SLA 耗时达标
  - 6. 并发更新至同一邮箱：10 线程把 10 个不同用户的邮箱改成同一个值，深度校验 1x200 契约与 9x409 业务错误提示，验证 UPDATE 路径唯一性防穿透
- **鉴权安全用例（4 条）**：
  - 无 Token 拦截(401)、错误 Token 拦截(401)、密码错误(401)、正常登录(200)（全量接入 `AssertUtil`、SLA 耗时、`LOGIN_SUCCESS_SCHEMA` 与 `ERROR_RESPONSE_SCHEMA`）

## 4. 持续集成与交付
- **CI/CD**：`.github/workflows/test_pipeline.yml`（GitHub Actions 矩阵多版本构建 Python 3.11/3.12/3.13 并行测试、MySQL 服务编排、健康检查轮询、Allure 命令行独立单文件 HTML 可视化报告编译与产物上传）
- **Docker 编排**：`Dockerfile`（纯后端精简镜像）+ `docker-compose.yml`（MySQL 8.0 映射 13306、Flask 映射 15000）
