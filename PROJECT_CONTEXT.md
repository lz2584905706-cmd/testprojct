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
- `performance/locustfile.py`：Locust 协程性能压测脚本（`ReadOnlyUser` 纯读基准与 `MixedLoadUser` 80/20 混合模型、`catch_response` 业务断言、UUID `perf_` 前缀造数与 `@events.test_stop` 自动清库）
- `performance/locust.conf`：Locust 无头自动化压测配置文件（统一托管并发数、爬坡速率、时长、HTML 与 CSV 报告输出）
- `scripts/`：故障注入验证探针（`probe_deadlock.py` 死锁复现探针、`probe_503.py` 行锁等待 1205 降级验证探针）

## 3. 测试用例统计（共 59 条）
- **正向业务用例（35 条）**：
  - 用户查询列表、用户详情查询（全量契约与 SLA 耗时校验）
  - 批量创建用户（11 条，含 1 条 Faker 动态造数用例，响应结构契约校验）
  - 批量更新用户（11 条数据驱动，全量响应与错误契约校验）
  - 更新接口真·幂等性用例（1 条，连续 3 次相同 PUT 请求断言无副作用与 200/code=0 稳定返回）
  - 批量删除用户（3 条数据驱动，全量响应与错误契约校验，`db.exists()` 物理落库校验）
- **反向异常用例（13 条）**：
  - 缺必填字段、空值、超长边界、非法邮箱格式、重复邮箱拦截（全量接入 SLA 耗时断言与 `ERROR_RESPONSE_SCHEMA` 错误契约校验）
- **高并发与高可用测试用例（7 条，全量实施双层深度断言与可观测性明细挂载）**：
  - 1. 并发创建同邮箱：10 线程验证 1x201+9x409+0x500，深度校验 201 响应体自增 ID 合法性与 409 精准提示语（"邮箱已被占用"）
  - 2. 并发删除同用户：10 线程验证 1x200+9x404+0x500，深度校验 200 删除契约与 404 错误响应（"用户不存在"），`db.exists()` 校验物理销毁
  - 3. 并发高频登录：10 线程同时发起鉴权登录，深度校验 `LOGIN_SUCCESS_SCHEMA` 契约合规与颁发 Token 精准值
  - 4. 并发更新同用户：10 线程同时更新同用户，深度校验各响应体契约，验证 MySQL 行锁串行化防死锁与最终一致性（杜绝幽灵写入）
  - 5. 并发读风暴：10 线程同时高频读取同一热点数据，深度校验 10 线程返回内容 100% 强一致（无脏读空读）与 SLA 耗时达标
  - 6. 并发更新至同一邮箱：10 线程把 10 个不同用户的邮箱改成同一个值，深度校验 1x200 契约与 9x409 业务错误提示，后端防御 MySQL 1213 死锁与 1205 锁等待超时
  - 7. 更新途中目标用户被删除：人工持锁放大「已读完用户、尚未 UPDATE」的窗口，另一事务删除该用户并提交，验证接口如实返回 404 而非谎报 200（后端以 UPDATE 影响行数 0 + 二次存在性确认实现）
- **鉴权安全用例（4 条）**：
  - 无 Token 拦截(401)、错误 Token 拦截(401)、密码错误(401)、正常登录(200)（全量接入 `AssertUtil`、SLA 耗时、`LOGIN_SUCCESS_SCHEMA` 与 `ERROR_RESPONSE_SCHEMA`）

## 4. 持续集成与交付
- **CI/CD**：`.github/workflows/test_pipeline.yml`（GitHub Actions 矩阵多版本构建 Python 3.11/3.12/3.13 并行测试、MySQL 服务编排、健康检查轮询、Allure 命令行独立单文件 HTML 可视化报告编译与产物上传）
- **Docker 编排**：`Dockerfile`（纯后端精简镜像）+ `docker-compose.yml`（MySQL 8.0 映射 13306、Flask 映射 15000）

## 5. 性能压测与瓶颈分析
- **压测模型**：基于 Locust 2.47.0（`gevent` 协程）构建 `BaseUserApiLoad` 公共基类与 `ReadOnlyUser`（100% 列表查询）、`MixedLoadUser`（80% 查询 + 20% 写入）双用户模型，`on_start` 单次登录注入 Token，强制校验 HTTP 状态码与业务 `code == 0` 防止假成功。
- **无头自动化与数据隔离**：通过 `performance/locust.conf` 托管 `--headless` 参数，自动导出 `reports/locust/` 离线单文件 HTML 与 4 份 CSV 统计表；停止时由 `@events.test_stop` 自动执行参数化删除 `perf_%@autotest.com`，保护 `alice`/`bob`/`carol` 只读基线。
- **实测基线数据（本地开发环境，30 并发 / 5 爬坡 / 20 秒混合压测）**：总请求 `277` 次，`0 (0.00%)` 失败，总吞吐 `14.56 req/s`，响应耗时中位数 `P50 = 970ms`、`P95 = 1,300ms`、`P99 = 1,500ms`。
- **四层瓶颈定位结论**：结合 20 并发纯读（P50 约 `600ms`、RPS 约 `11~13.4`）与 30 并发混合（RPS 停滞于 `12~14.5`、P50 翻倍）的对比拐点，排除压测端限制后定位瓶颈为：① Flask 单进程 Werkzeug 开发服务器受 Python GIL 争抢；② `backend/app.py` 每次请求新建/销毁 `pymysql.connect` 短连接（无连接池）；③ `GET /api/users` 无 `LIMIT` 分页全表序列化与 `POST` 唯一索引/事务刷盘开销。
