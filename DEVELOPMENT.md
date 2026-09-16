# L3 异地开发指南

本仓库属于 [CodePick 四层平台](https://github.com/jayson2hu/codepick-docs)。建议四个代码仓库保持同级目录，以便查阅关联实现；每个项目使用独立虚拟环境。

## 克隆与环境

需要 Git、Python 3.12 和 Node.js 20 或更新版本。以下命令都从本仓库根目录执行。

```sh
git clone https://github.com/jayson2hu/pickblog.git
cd pickblog
python -m venv .venv
```

激活环境：Windows PowerShell 使用 `.venv\Scripts\Activate.ps1`；macOS/Linux 使用 `source .venv/bin/activate`。随后执行：

```sh
python -m pip install -e ".[dev]"
python scripts/l3_smoke.py
python scripts/run_reader_api.py
```

## 当前运行模式

后端 API 默认在独立开发模式运行，使用 L2 stub、沙箱计费和 mock 邮件。`.env.example` 是配置参考，真实配置自行保存在未跟踪的 `.env` 或进程环境变量中，按各启动入口说明加载。

前端需要 Node.js 20 或更新版本，在另一个终端运行：

```sh
cd apps/reader-web
npm ci
npm run dev
```

前端检查：`npm run typecheck`。完整交接验证：先在前端目录执行 `npx playwright install chromium`，再回仓库根目录运行 `python scripts/l3_verify.py`。真实 L2、支付、邮件和基础设施联调的门禁见 docs/L3-final-integration-checklist.md。

Playwright 默认在 `127.0.0.1:3100` 启动独立 reader-web，避免误复用宿主机 3000 端口；可用 `PLAYWRIGHT_PORT` 覆盖。最小 Ubuntu 镜像还需安装 Playwright 报告的 Chromium 共享库。

## M2 真实 L2 联调

先按 agentic 文档在 `127.0.0.1:8200` 启动 L2 HTTP，再启动 Reader API：

```sh
L3_USE_STUB_L2=false \
L2_BASE_URL=http://127.0.0.1:8200 \
READER_API_HOST=127.0.0.1 \
READER_API_PORT=8100 \
.venv/bin/python scripts/run_reader_api.py
```

前端使用同源代理，关闭演示回退：

```sh
cd apps/reader-web
READER_API_BASE=http://127.0.0.1:8100 \
READER_API_PROXY_TARGET=http://127.0.0.1:8100 \
READER_USE_DEMO_FALLBACK=false \
NEXT_TELEMETRY_DISABLED=1 \
npm run dev -- --hostname 127.0.0.1 --port 3200
```

M2 专用浏览器测试不拦截 API：

```sh
PLAYWRIGHT_PORT=3200 npm run test:e2e:m2
```

正常测试验证 M1 文章列表、详情、六维评分和中文翻译。停止 L2 后运行
`m2-tests/reader-upstream-error.spec.ts`，页面必须显示可重试错误；恢复 L2
后无需重建 Reader API 或前端即可继续读取。真实模式下不得设置
`READER_USE_DEMO_FALLBACK=true`。

## Public API 搜索与上游错误验收

Public API 使用相同 L2 服务时可启动在另一个 loopback 端口：

```sh
L3_USE_STUB_L2=false \
L2_BASE_URL=http://127.0.0.1:8200 \
PUBLIC_API_HOST=127.0.0.1 \
PUBLIC_API_PORT=8001 \
.venv/bin/python scripts/run_public_api.py

`PUBLIC_API_HOST`、`PUBLIC_API_PORT` 和 `PUBLIC_API_RELOAD` 均由启动脚本读取；
reload 默认关闭，适合跨进程验收和本地编排。

curl --get -H 'X-API-Key: cp_test_key' \
  --data-urlencode 'q=postgres' \
  --data 'limit=10' \
  http://127.0.0.1:8001/v1/search
```

`q` 会下推到 L2 并在分页前搜索；MCP `search` 使用同一 provider 语义。专项测试：

```sh
.venv/bin/python -m pytest -c pytest.ini tests/test_public_api_search.py
```

2026-09-16 的无 API mock 跨进程验收使用临时 SQLite、真实 L2 HTTP 和关闭 stub
的 Public API，得到唯一命中文章并返回 `next_cursor=null`。停止 L2 后同一请求返回
503 `l2_unavailable`、`retryable=true` 和 `Retry-After: 2`；非法游标返回 400
`invalid_request`。服务都只绑定 `127.0.0.1`，未连接真实业务数据库或付费模型。
另一次验收把 L3 用户、API key 和配额表迁移到一次性 PostgreSQL 16，使用真实
L2 HTTP 与真实 Public API 进程连续搜索两次；结果仍为唯一 `id=2`，数据库中的
`api_usage_daily.count=2`。PostgreSQL 仅绑定 `127.0.0.1:55440`，结束后容器已删除。


## 交接范围

提交包括当前源码、测试、迁移、配置示例与项目文档。依赖目录、构建产物、本地数据库、采集运行数据、日志和凭据不随仓库分发，需要在新环境重新安装或配置。

各层状态与验收证据见项目 README 和 docs；本文提供恢复开发的入口，不代表本次发布重新完成生产环境验收。

## M3 用户隔离与认证模式

本地默认 `L3_AUTH_LOGIN_MODE=development`。该模式仍是开发便利登录，但每个规范化
邮箱会创建或读取独立用户，不再固定为 `user_id=1`。使用 SQLAlchemy 后端时用户
记录和所有账户状态都保存在 `DATABASE_URL` 指向的 L3 数据库中：

```sh
L3_AUTH_LOGIN_MODE=development L3_REPOSITORY_BACKEND=sqlalchemy L3_QUOTA_BACKEND=sqlalchemy DATABASE_URL=postgresql+psycopg://codepick:codepick@127.0.0.1:5432/codepick_l3 .venv/bin/python scripts/run_reader_api.py
```

生产型预检必须设置 `L3_AUTH_LOGIN_MODE=external`。此时开发邮箱登录端点返回 503，
防止把任意邮箱当成已验证身份。该设置只关闭开发登录；真实 OIDC、magic link 或其他
身份提供商仍需后续接入。

Reader Web 已升级到 Next.js 16.3.5，要求 Node.js 20.9 或更高版本。恢复依赖和检查：

```sh
cd apps/reader-web
npm ci
npm audit --audit-level=low
NEXT_TELEMETRY_DISABLED=1 npm run typecheck
NEXT_TELEMETRY_DISABLED=1 npm run build
npm run test:e2e
```

标准 Ubuntu 可用 `npx playwright install --with-deps chromium` 安装浏览器及系统库。
没有 sudo 时，可单独提供浏览器和共享库，并通过
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 与 `LD_LIBRARY_PATH` 指定；不要把下载的
浏览器、deb 或解压目录提交到仓库。
