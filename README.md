# 用户管理接口自动化测试项目

[![CI Pipeline](https://github.com/lz2584905706-cmd/testprojct/actions/workflows/test_pipeline.yml/badge.svg)](https://github.com/lz2584905706-cmd/testprojct/actions/workflows/test_pipeline.yml)

基于 Flask + Pytest + Allure + Locust 搭建的企业级接口自动化测试与性能压测工程，覆盖用户管理模块的增删改查、JsonSchema 契约校验、高并发锁竞争与性能拐点压测。

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Flask + MySQL 8.0 |
| 测试框架 | Pytest 9.2.0 |
| 性能压测 | Locust 2.47.0（`gevent` 协程 + Headless 自动化报告） |
| 数据驱动 | YAML + Faker 动态造数引擎 |
| 持续集成 | GitHub Actions CI/CD 流水线 |
| 容器化 | Docker + Docker Compose 编排 |
| 质量监控 | SLA 响应耗时监控 + Flaky 局部重试 |
| 报告与日志 | Allure 2.16 + Locust HTML/CSV 性能报告 + 日志记录 |
| 网络与数据库 | Requests + PyMySQL |

## 项目结构

```
user_api_test/
├── backend/
│   └── app.py              # Flask 后端（6个REST接口、Token鉴权、1213/1205锁重试与503降级）
├── common/
│   ├── api_client.py       # HTTP 请求封装（自动登录、异常处理、Fiddler代理）
│   ├── assert_util.py      # 断言封装（状态码/字段/SLA耗时/JsonSchema失败自动挂载Allure）
│   ├── data_faker.py       # Faker 动态造数工厂（唯一邮箱/随机中文名）
│   ├── db_client.py        # 数据库操作封装（参数化查询/exists/delete）
│   ├── logger.py           # 日志模块
│   ├── schemas.py          # JsonSchema 响应契约模型
│   └── yaml_util.py        # YAML 数据读取与动态函数替换
├── config/
│   └── config.py           # 多环境配置（dev/test）
├── data/
│   └── user_data.yaml      # 测试数据（数据驱动）
├── performance/
│   ├── locustfile.py       # Locust 协程压测脚本（ReadOnlyUser/MixedLoadUser 与自动清库）
│   └── locust.conf         # Locust 无头自动化默认配置文件
├── scripts/
│   ├── probe_deadlock.py   # MySQL 1062/1213 死锁复现探针
│   └── probe_503.py        # MySQL 1205 锁超时触发 503 降级验证探针
├── testcases/
│   ├── test_user_api.py             # 正向用例（CRUD数据驱动 + 真·幂等性）
│   ├── test_user_api_negative.py    # 反向用例（缺字段/边界/重复邮箱）
│   ├── test_user_api_concurrent.py  # 高并发与竞态穿越用例（7大并发场景）
│   └── test_token_auth.py           # 鉴权用例（401/登录）
├── sql/
│   └── init.sql            # 建表语句
├── conftest.py             # Pytest fixture（清表、api/db实例、cleaner数据回收）
├── pytest.ini              # Pytest 配置
├── requirements.txt        # 后端生产运行依赖
├── requirements-dev.txt    # 测试与压测全量开发依赖
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
.\.venv\Scripts\pytest.exe -q

# 生成 Allure 报告
allure serve reports/allure
```

## 性能压测（Locust）

> 前提：请先在独立终端启动后端服务 `.\.venv\Scripts\python.exe backend\app.py`。

```powershell
# 1. 无头自动化一键压测并导出 HTML/CSV 报告（读取 performance/locust.conf）
.\.venv\Scripts\python.exe -m locust --config performance/locust.conf MixedLoadUser

# 2. 切换为纯读基准压测模型
.\.venv\Scripts\python.exe -m locust --config performance/locust.conf ReadOnlyUser

# 3. 临时调整并发用户数与时长（命令行参数覆盖配置文件）
.\.venv\Scripts\python.exe -m locust --config performance/locust.conf MixedLoadUser -u 80 -r 10 -t 30s

# 4. 启动 Web UI 实时监控大屏（访问 http://localhost:8089）
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --class-picker

# 5. 使用 Edge 浏览器查看离线压测 HTML 报告
Start-Process msedge "E:\DoubaoWork\user_api_test\reports\locust\report_30u_20.html"
```

- **本地基线实测（30 并发 / 5 爬坡 / 20 秒混合压测）**：`277` 次请求 `0 (0.00%)` 失败，聚合吞吐 `14.56 req/s`，`P50 = 970ms`、`P95 = 1,300ms`、`P99 = 1,500ms`；停机自动清理 `perf_` 压测数据，只读基线零污染。
- **瓶颈分析结论**：20 并发纯读至 30 并发混合阶段吞吐停滞于 `12~14.5 RPS` 且耗时翻倍，定位原因依次为 Flask 单进程开发服务器 GIL 争抢、无连接池短连接建连开销、以及无分页全表查序列化与写索引落盘叠加耗时。

## 功能特性

- **数据驱动**：测试数据与代码解耦，YAML 维护，支持 `${random_email()}` 等动态占位符
- **动态造数引擎**：集成 Faker 并采用内存递归安全替换，彻底避免唯一键与并发数据冲突
- **双重断言与高阶封装**：既校验接口响应状态码与业务 code，又通过 `DbClient.exists()` 严苛验证数据物理落库与物理销毁
- **数据回收站 (Teardown)**：引入 `cleaner` Fixture 精准回收测试临时脏数据，0 数据污染，环境高度幂等
- **全量 SLA 耗时监控**：正向接口、单用户查询、鉴权登录与异常参数校验全量内置响应耗时 SLA 断言，自动拦截性能退化
- **全场景契约闭环测试**：引入 `JsonSchema` 覆盖用户 CRUD、Token 登录鉴权及全局统一异常响应（400/401/404/409），更新与删除全分支错误契约 100% 校验，彻底杜绝契约破坏
- **全工程统一断言规范**：正向、反向、鉴权用例 100% 接入 `AssertUtil`，任何断言失败均自动捕获请求与响应正文并附加至 Allure 报告
- **高并发双层深度断言**：构建涵盖增、删、改、查、鉴权及竞态穿越等 7 大场景的高并发测试体系，不仅校验 HTTP 协议状态码分布，更穿透断言响应体业务字段、自增 ID 合法性、强一致性与 JsonSchema 契约，彻底杜绝多线程环境下的数据串号与假报错
- **数据库瞬时故障自愈**：捕获 MySQL 死锁(1213)与锁等待超时(1205)自动重试一次，仍失败按 RFC 返回 503 与 `Retry-After`，避免瞬时故障退化为 500；配合人工持锁的故障注入脚本可端到端验证该降级链路
- **并发竞态穿越校验**：人工持锁放大时间窗口，验证「更新请求已读取用户、随后被其它事务删除」时接口如实返回 404，而非谎报更新成功
- **并发秒级可观测性**：测试执行自动生成格式化《并发观测明细表》挂载至 Allure 附件，并以具体请求序号精准捕获错误响应
- **真·幂等性保障**：严格遵循 HTTP 语义（RFC 7231）实装连续 3 次相同 PUT 请求断言，验证无副作用与结果幂等
- **分层测试**：打标 `smoke`、`regression`、`security`、`concurrent`，支持秒级筛选
- **CI/CD 持续集成**：GitHub Actions 云端 Python 3.11/3.12/3.13 矩阵并行构建，自动化拉起 MySQL、健康检查轮询并产出 Allure 单文件 HTML 报告
- **Docker 容器化**：提供精简 `Dockerfile` 与多容器编排 `docker-compose.yml`，规避宿主机端口冲突
- **Locust 性能压测与自动清库**：基于 `gevent` 协程封装 `ReadOnlyUser` / `MixedLoadUser` 双模型，支持 `on_start` Token 注入、`catch_response` HTTP+业务 `code==0` 防假成功断言、UUID `perf_` 前缀防碰撞造数及 `@events.test_stop` 精准清库，搭配 `locust.conf` 一键产出单文件 HTML 与 CSV 报告

## 测试覆盖

共 59 条用例（含 1 条 Faker 动态造数用例、1 条真·幂等性用例、7 条高并发与竞态用例），单次全量执行约 18~25 秒，全绿通过。

| 模块 | 覆盖场景 |
|---|---|
| 查询用户列表 | 接口返回条数与数据库一致、契约结构校验 (GET) |
| 查询单个用户 | 正常查询（含契约校验 GET）、用户不存在(404)、id=0(404)、负数id(路由层404) |
| 创建用户 | 正常创建(含中文/长名/50字符边界/禁用状态/Faker动态造数/写契约校验 POST 201)、缺字段(400)、空字符串(400)、null字段(400)、重复邮箱(409)、name超长(400)、email超长(400)、非法邮箱格式(400)、status非法值(400)、不传status默认值 |
| 更新用户 | 只改name、只改email、只改status、同时改多个字段(含全量更新与错误契约校验 PUT 200/400/404/409)、用户不存在(404)、改成已存在邮箱(409)、name为空(400)、name超长(400)、非法邮箱格式(400)、status非法值(400)、连续3次相同PUT真·幂等性校验(200无副作用) |
| 删除用户 | 正常删除(含契约校验 DELETE 200)、用户不存在(404且含错误契约)、id=0(404且含错误契约) |
| 高并发与高可用 | 涵盖 7 大场景：①并发创建同邮箱(1x201+9x409)；②并发删除同用户(1x200+9x404)；③并发高频登录(10x200)；④并发更新同用户(行锁防死锁)；⑤并发读风暴(10线程SLA耗时监控)；⑥并发更新至同一邮箱(唯一约束在 UPDATE 路径同样生效，后端防御 MySQL 1213 死锁与 1205 超时，1x200+9x409)；⑦更新途中目标用户被删除(人工持锁放大竞态窗口，接口如实返回 404 而非谎报 200) |
| 鉴权 | 无Token(401)、错误Token(401)、密码错误(401)、正确登录返回Token |
