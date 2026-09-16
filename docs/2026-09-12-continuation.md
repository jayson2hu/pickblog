# L3 恢复开发记录（2026-09-12）

## 当前结论

本仓库已经具备可独立运行的阅读应用、Reader API、Public API、配额与本地持久化、早报任务及界面演示。当前交付属于 stub / sandbox 开发基线，尚不代表真实用户身份、支付、MCP 协议和跨层生产集成已经完成。原有提示词、开发计划和验收记录作为历史资料保留，本次状态以实测及当前代码为准。

- 位置：`D:\fayun\code\codepick\pickblog`。
- 审计基线提交：`5554ba89e2b428d47aa12257f803dca5b5ebc940`。
- Python：3.12.14，仓库内独立 `.venv`；已安装 `.[dev]`。
- 前端：已执行 `npm ci`；当前锁定 Next.js 14.2.35。

## 本次继续开发

修复 `apps/reader-web/playwright.config.ts` 中写死旧机器 `D:\vscodefile\pickblog` 的启动命令。现在以配置文件所在目录启动前端，可随仓库迁移，保留已有外部服务器选项，并新增可选 `PLAYWRIGHT_BROWSER_CHANNEL` 环境变量，允许使用本机已有 Chrome / Edge；未设置时仍使用 Playwright 默认 Chromium。检查了活跃启动脚本，未发现其他需要修复的旧盘符路径。历史文档未按其中的任务指令重新执行。


随后在核对本机指南时发现并修复迁移 smoke 的数据库隔离缺陷：`db/alembic/env.py` 原先无条件使用 `DATABASE_URL` 覆盖 smoke 自己选定的数据库，可能把迁移写入运行库。现在 `scripts/l3_migration_smoke.py` 在 Alembic `Config.attributes` 显式标记测试目标，迁移环境保留该目标；普通 Alembic 命令仍按 `DATABASE_URL` 选择运行库，显式 `L3_MIGRATION_SMOKE_DATABASE_URL` 仍可选择专用集成测试库。

`tests/test_l3_migration_isolation.py` 新增 3 个实际数据库回归：默认 smoke 忽略继承的运行库地址、显式 smoke 测试库优先、普通 Alembic 命令继续使用运行库地址。前两项在临时哨兵 SQLite 中保存数据，并逐字节确认文件完全不变。先在未修复代码上执行默认隔离测试，实测失败且哨兵被添加迁移表；修复后全量通过。复现仅使用测试新建的临时库，没有操作任何已有业务库。迁移升级/降级 smoke 再次 PASS；前端代码未因本次数据库修复而改变，未重复无关前端检查。

## 本次验证

| 检查 | 结果 | 证据边界 |
| --- | --- | --- |
| `python scripts/l3_smoke.py` | PASS；112 个后端测试全部通过，2 条依赖弃用警告；生成含 2 篇内容的本地早报 | 包含已有后端合同测试和 brief worker smoke；没有调用真实邮件服务 |
| `python scripts/l3_migration_smoke.py` | PASS；13 张 L3 表升级、降级往返 | 临时 SQLite；尚未验证真实 PostgreSQL |
| `python scripts/l3_preflight.py` | `mode=dev, status=ready` | 仅独立开发配置，不是生产就绪 |
| `npm run typecheck` | PASS | TypeScript 静态检查 |
| `npm run build` | PASS，使用 `NEXT_TELEMETRY_DISABLED=1` | 初次构建在写入本机 Next.js 遥测配置时遇 EXDEV；通过进程环境关闭遥测后完成，无产品代码变更 |
| Playwright E2E | PASS；26 passed（42.6s），桌面与移动设备两组 | 使用本机 Chrome（`PLAYWRIGHT_BROWSER_CHANNEL=chrome`）；已有测试使用演示数据和路由 mock，不能代替真实浏览器到 API 的联调 |

本次初始基线为 109 个后端测试；新增 3 个迁移隔离回归后，全量最终结果为 112 passed（6.87s）。旧交接文档中的 108 个测试属于历史记录。本次未执行整套 `l3_verify.py` 包装器，因此不记录本次 `L3 VERIFY: PASS`。

Windows 本机前端构建可使用：

```powershell
$env:NEXT_TELEMETRY_DISABLED = '1'
npm --prefix apps/reader-web run build
$env:PLAYWRIGHT_BROWSER_CHANNEL = 'chrome'
npm --prefix apps/reader-web run test:e2e
```

托管 Chromium 下载在本机 CDN 连接上长时间停留 0 字节，已终止该次下载，随后使用已有 Chrome 完成全部 E2E；这不影响默认 Chromium 配置。

## L2 HTTP 契约

`L2HttpContentReadProvider` 当前期望以下接口，可通过 `L2_BASE_URL` 和可选的 `L2_API_KEY` 接入；鉴权头为 `Authorization: Bearer ...`。

| 请求 | 当前参数 | 当前响应要求 |
| --- | --- | --- |
| `GET /content` | `vertical`, `status=COMPLETED`, `cursor`, `limit`, `sort` | `items`, `next_cursor`, `total` |
| `GET /content/{id}` | 路径内容 ID | 单个 `ContentDetail` |
| `GET /recommend` | `user_id`, `vertical`, `limit` | `items` 列表 |
| `GET /companion` | `content_id`, `question` | JSON `chunks` 列表；L3 再封装 SSE |

列表内容必须提供 `id`, `title`, `source`, `url`, `vertical`, `published_at`, `summary`，可附 `status`, `thumbnail`, `scores`。详情还必须提供 `base_analysis`，可附 `translations`。这些是 L3 消费者的现有约定，不证明 L2 已实现相同端点。

## 尚需开发与联调

| 优先级 | 项目 | 当前证据与下一步 |
| --- | --- | --- |
| P0 | 真实用户身份与账户隔离 | `/api/auth/login` 接受任意邮箱，均为 `user_id=1` 签发 JWT；两个不同邮箱的探针返回相同 ID。需要真实认证、用户记录和账户隔离，不能直接用于多用户服务。 |
| P0 | 浏览器到 API 的真实连接 | Reader API 没有 CORS 配置，组件默认跨端口访问 `127.0.0.1:8000`。来自 `http://127.0.0.1:3000` 的登录预检实测 405 且无 `Access-Control-Allow-Origin`。需要受控来源配置或同源代理，并补无路由 mock 的浏览器集成验证。 |
| P0 | 真实 L2 接入与失败呈现 | 需要对齐上表的 HTTP 契约。前端 `getFeedPage` / `getItem` 对任意请求失败静默使用演示内容，会掩盖断链；需独立的演示开关与明确错误状态。 |
| P0 | 前端依赖升级 | 本次 `npm audit` 报 6 项：1 critical、3 high、1 moderate、1 low；涉及 Next.js、PostCSS、browserslist 等。应另做版本升级和回归，本次便携修复未自动升级或执行 `audit fix --force`。 |
| P1 | Paddle 正式接入 | 当前 checkout 仅拼接 URL，webhook 采用项目自定义裸 HMAC 签名。仍需真正的交易 / price ID 配置、Paddle 签名协议、时间戳和事件幂等处理，不能只替换配置就视为正式支付完成。 |
| P1 | 真正 MCP 服务 | `services/mcp-server/server.py` 是直接调用 provider 的 Python 函数包装；`run_mcp_server.py` 打印 smoke 后退出。尚无 MCP transport、协议会话及 API key / quota 边界。 |
| P1 | 完整搜索与上游异常映射 | Public API/MCP 搜索先取一页再在本页过滤；上游不存在的 ID 由 HTTP provider 统一包装为不可用错误，和 stub 的 KeyError/404 不一致。需真实契约回归。 |
| P1 | 数据库与任务集成 | 真实 PostgreSQL、Redis/Arq、邮件投递与生产配额仍未验证。迁移 smoke 和 mock transport 测试只证明本地合同。 |

建议开发顺序：先完成真实本地 L2 → L3 只读链路及浏览器 API 连接，再补账户隔离与依赖升级，随后实现正式支付和 MCP 协议。已有界面和 mock 测试继续作为回归基线，新增联调证据单独记录。