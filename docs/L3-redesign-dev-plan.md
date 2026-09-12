# CodePick L3 — 前端重设计 + 后台 Taxonomy 开发计划（交付 Codex）

> 本文是可执行开发计划。实现者**没有**我们的对话上下文，请只依据本文 + 仓库现状 + 视觉原型。
>
> **视觉与交互的唯一事实来源（source of truth）：** `docs/L3-redesign-v2-preview.html`
> （单文件可交互原型，含：首页信息流、详情、早报、开发者页、订阅页、**管理后台**、登录态自适应侧栏、深色模式、受众/分类切换。打开即可点。）
>
> 本计划把该原型落到真实代码：**Next.js App Router 前端**（`apps/reader-web`）+ **FastAPI 后端**（`services/reader-api`、`services/public-api`、`services/shared/codepick_l3`）+ **Alembic 迁移**（`db/`）。

---

## 0. 仓库现状（实现前先读）

- 前端：`apps/reader-web`（Next.js App Router，`app/[locale]/...`，Tailwind，设计令牌在 `app/globals.css`）。
  - 页面：`app/[locale]/page.tsx`(信息流)、`items/[id]/page.tsx`(详情)、`brief/page.tsx`、`login/page.tsx`(账户大杂烩)。
  - 组件：`components/Header.tsx`、`InterestOnboarding.tsx`、`CompanionWidget.tsx`、`ReadingActions.tsx`、`BriefGate.tsx`、`BillingPanel.tsx`、`ApiKeyPanel.tsx`、`LoginForm.tsx`、`TrackedContentLink.tsx`。
  - 数据层：`lib/api.ts`（`ContentSummary`/`ContentDetail` 类型、`getFeed()`/`getItem()`，失败回退本地 mock）。
- 后端（Reader API，JWT，`/api`）：`services/reader-api/reader_api/routers/`：`feed.py`、`read.py`、`companion.py`、`events.py`、`library.py`、`briefs.py`、`billing.py`、`api_keys.py`、`auth.py`。
- 后端（Public API，API Key，`/v1`）：`services/public-api/public_api/routers/v1.py`（`/today /search /items/{id} /trending /sources /verticals`）。
- 共享库：`services/shared/codepick_l3/`：`models.py`、`schemas.py`、`repository.py`、`provider.py`(ContentReadProvider，读 L2)、`public_contract.py`(公共字段过滤)、`auth.py`(`current_user`/`require_plan`/`has_plan`)、`config.py`、`usage.py`、`billing.py`、`briefs.py`、`email.py`。
- 迁移：`db/alembic/versions/0001_l3_owned_tables.py`。已有表：`users, subscriptions, user_interests, user_follows, reading_events, briefs, bookmarks, api_keys, api_usage_daily, companion_usage`。
- 校验脚本（必须保持绿）：`python scripts/l3_verify.py`（preflight → migration smoke → backend pytest **108 passed** → reader-web typecheck/build → Playwright **26 passed**）。CI：`.github/workflows/l3-ci.yml`。

### 必须遵守的架构约束（L3 契约，勿违反）
1. **L2 只读**：内容与六维评分来自上游 L2，经 `ContentReadProvider` 读取，**L3 不得修改源判断**。新增的"读时""入选理由"是 **L3 派生的展示字段**（见 §6），非改 L2。
2. **只拥有 L3 自己的表**：新表必须是 L3 owned，并写进 Alembic 迁移（新建 `0002_*`）。
3. **`/api` 与 `/v1` 信任边界**：`/api`=JWT 用户态；`/v1`=API Key。两者代码隔离，勿交叉 import 对方鉴权/仓储。
4. **公共字段边界**：`/v1` 与 MCP 只能返回 `public_contract.py` 允许的公共字段，且仅 `COMPLETED`。新增字段若要进 `/v1` 必须确认是公共安全字段。
5. **独立开发默认值**：默认 stub-L2 / 内存仓储 / sandbox 计费 / mock 邮件；真实外部服务在最终集成时再开。新功能要能在 stub 模式下本地跑通与测试。
6. **i18n**：所有用户可见文案需 EN/ZH 双份（沿用现有组件的 locale 模式）。

---

## 1. 目标 / 非目标

**目标**
- 用原型的视觉与信息架构替换现有朴素 UI（编辑质感、深色模式、可访问性达标）。
- 落地"阅读决策层"：领域筛选、读时、入选理由、免登录稍后读、排序、加载更多。
- 详情页：封面、原文链接、**段落级中英对照**、六维含义解释、**对话式 AI 速读**（预设追问 + 流式 + 可见配额 + Pro 无限）。
- **登录态自适应**：未登录 / 登录-Free / 登录-Pro 三态，**Pro 不再有任何升级打扰**。
- **后台可配置 Taxonomy**：分类（categories）与受众（audiences）由**管理后台**增删改，阅读端按用户所属受众渲染分类；对外经 `/v1/taxonomy`。
- 新增「开发者」页（API 文档 + 控制台）与「订阅」对比页；账户页瘦身。

**非目标（本期不做）**
- 不接真实 L2 / Postgres / Redis / Resend / Paddle 生产联调（仍按 stub/sandbox）。
- 不做内容抓取与评分（属于 L2）。
- 管理后台不做完整 RBAC/审计，仅 `is_admin` 单角色门禁 + 基本 CRUD。

---

## 2. 交付物总览（Epics）

| Epic | 名称 | 主要产物 |
|---|---|---|
| A | 设计系统 + 外壳 | `globals.css` 令牌、深色模式持久化、`Header`(含 auth slot)、a11y 基线 |
| B | 阅读决策层（首页） | 筛选/排序/读时/入选理由/稍后读/加载更多/Hero(首访)/移除面向用户的内部指标 |
| C | 内容详情 | 封面、原文链接、段落级双语、六维解释、对话式 AI 速读、阅读操作态 |
| D | 登录态自适应 | `/api/me`、plan 感知侧栏（三态）、账户菜单、稍后读本地→登录同步 |
| E | Taxonomy + 管理后台 | 新表/迁移、`/api/taxonomy` + `/api/admin/*`、`/v1/taxonomy`、Admin UI、受众分配 |
| F | 开发者页 | `/developers` 文档 + 控制台（密钥/用量/MCP），从账户页迁出 ApiKeyPanel |
| G | 订阅页 | `/pricing` Free×Pro 对比 + 情境化升级时机 |
| H | 早报页打磨 | "为什么是这几条" + 读时 + 邮箱订阅 + Pro 个性化提示 |

> 原型每个视图对应一个 Epic，实现时对照 `docs/L3-redesign-v2-preview.html` 同名区块。

---

## 3. 实施顺序与里程碑（建议 PR 拆分，每个 PR 后 `l3_verify` 必须绿）

- **M1（基础）** Epic A → 设计系统 + Header/Shell + 深色模式 + a11y 基线。`page.tsx` 视觉迁移但不改数据。
- **M2（阅读核心）** Epic B + C → 首页决策层 + 详情页（含对话式伴读、双语、稍后读本地版）。后端加派生字段（§6）。
- **M3（账号）** Epic D → `/api/me`、登录态侧栏三态、稍后读登录同步、账户菜单。
- **M4（Taxonomy）** Epic E → 迁移 + 后端 taxonomy/admin 接口 + 管理后台 UI + 阅读端消费 taxonomy。
- **M5（分发与商业化）** Epic F + G + H → 开发者页、订阅页、早报打磨、账户页瘦身。

每个 PR：① 不破坏现有 108 backend + 26 Playwright；② 新增对应测试；③ 更新 i18n 文案；④ `docs/L3-completion-audit.md` 增量勾选。

---

## 4. Epic 详述

### Epic A — 设计系统 + 外壳
**前端**
- 重写 `app/globals.css` 设计令牌，对照原型 `:root` / `[data-theme="dark"]`（靛蓝主色 `--accent:#4f46e5`、中性灰阶、圆角/阴影、`--font`）。保留 Tailwind；令牌用 CSS 变量，Tailwind 主题映射到变量。
- **深色模式**：`data-theme` 挂 `<html>`，持久化到 `localStorage('cp_theme')`；尊重 `prefers-color-scheme` 首次默认；尊重 `prefers-reduced-motion`。
- 重写 `components/Header.tsx`：品牌 + 主导航（阅读/早报/开发者/订阅）+ 右侧 主题/语言/`authSlot`（§Epic D）。粘性玻璃拟态。
- **a11y 基线**：`:focus-visible` 轮廓、`aria-label`、`role`、最小触控 44px、跳到主内容链接、语义化标签。卡片用 `<article tabindex role=link>` + 键盘 Enter。
**验收**
- 浅/深色切换正常并刷新保留；键盘可遍历导航与卡片；Lighthouse a11y ≥ 95；现有页面视觉迁移后 Playwright 仍绿（必要时更新选择器）。

### Epic B — 阅读决策层（首页 `app/[locale]/page.tsx`）
**前端**
- 顶部 **Hero 价值条**：仅未登录展示，可关闭（`localStorage('cp_hero_dismissed')`）；含价值主张 + 信任要素 + "如何评分"解释弹层。
- **筛选栏**：领域 chips（来自 taxonomy/当前受众，见 Epic E；M2 阶段可先用 `/api/feed` 的 vertical 去重兜底）+ 排序段（推荐/最新/最高分，映射 `/api/feed?sort=`）。
- **信息流卡片**：封面（见 §6 缩略图）、来源/领域/**读时**标签、标题、摘要、**入选理由**(§6)、质量分 chip、**+ 稍后读**按钮。
- **头条精选**：列表首条做大卡 + 质量分环（hover 显示六维 tooltip）。
- **加载更多 / 分页**：`/api/feed` 是 **cursor 分页**（`cursor`+`next_cursor`），实现"加载更多"或基于 cursor 的页码；原型里的数字分页仅示意。
- **移除面向读者的内部北极星指标**（DRCL 等）——它属于运营视角，不在用户首屏。
- **稍后读（本地优先）**：未登录存 `localStorage('cp_saved')`；登录后合并同步到 `/api/bookmarks`（见 Epic D）。
**后端**
- `/api/feed` 已支持 `vertical/sort/cursor/limit`，无需大改；确认返回项带 §6 的 `read_time_minutes` 与 `reason`（在序列化层补）。
**验收**
- 切领域/排序/加载更多生效；未登录可加入稍后读并刷新保留；卡片有读时与入选理由；Hero 可关闭且登录后不显示。

### Epic C — 内容详情（`app/[locale]/items/[id]/page.tsx` + 组件）
**前端**
- 顶部封面 + 标签行 + 标题 + 摘要 + **原文链接来源**（`item.url`，新标签打开，`rel=noopener`）。
- **段落级中英对照**：`正文` 面板支持「对照 / EN / 中文」三态切换（数据见 §6 `paragraphs`；无分段数据时回退整段 summary/base_analysis）。
- **六维评分**：每维 hover/聚焦显示含义 tooltip；"如何评分"解释（评分来自 L2，L3 只读）。
- 重写 `components/CompanionWidget.tsx` → **对话式 AI 速读**：
  - 多轮气泡（保留会话历史，前端态）；**预设追问**按钮（用更简单的话 / 给背景 / 术语表 / 横向对比）；**流式**渲染（沿用现有 SSE `/api/companion`，逐字光标）；**可见配额**条。
  - **Pro 无限**：`plan==='pro'` 时不显示配额、不计数、不被 429。
- 重写 `components/ReadingActions.tsx`：标记深读/收藏(=稍后读)/不感兴趣 → 明确"已选中"态 + 失败回退本地 + 未登录显示"登录以同步"行内提示（不再用裸 401 文案）。
**后端**
- `companion.py`：保留 SSE + 配额；**新增配额可见性**：响应头返回 `X-Companion-Remaining`/`X-Companion-Limit`，或新增 `GET /api/companion/quota`（当日 used/limit/plan）。多轮：请求体允许携带可选 `history`（仅作上下文，stub provider 可忽略）。
- `read.py`：详情响应补 `read_time_minutes`、`reason`、（若 provider 提供）`paragraphs`。
**验收**
- 双语三态切换正确；伴读多轮 + 预设 + 流式可用；Free 配额可见且用尽 429 提示升级；Pro 无配额限制；原文链接可点。

### Epic D — 登录态自适应
**前端**
- 新增会话/资料获取：`lib/session.ts` 读 `localStorage('codepick_token')` → 拉 `GET /api/me` 得 `{email,nickname,plan,locale,audience,is_admin}`；提供 `useSession()`。
- `Header` 的 `authSlot`：未登录=「登录」按钮；登录=头像 + 名称 + plan 徽章 + 下拉**账户菜单**（我的稍后读 / 我的关注领域 / 账户与订阅 /（admin 显示）管理后台 / 升级或切回 / 退出）。
- **plan 感知侧栏**（首页 `aside`，对照原型 `renderSidebar` 三态）：
  - **未登录**：早报订阅(邮箱) + 稍后读计数 + Pro 卡片（转化）。
  - **登录-Free**：问候 + 关注领域 chips + 稍后读列表 + **一行可关闭**的轻量升级提示（不再用整块卡片打扰）。
  - **登录-Pro**：问候(PRO 徽章) + 个性化早报已开启 + 关注领域 + 稍后读列表，**零升级元素**。
- **稍后读登录同步**：登录后把 `localStorage('cp_saved')` 合并 PUT 到 `/api/bookmarks` 并清本地缓存。
- 升级入口改为**情境化**：仅在价值点出现（伴读配额用尽、Pro 专属功能处），不全局常驻。
**后端**
- 新增 `GET /api/me`（`current_user` → 资料 + plan + audience + is_admin）。
- 确认 `library.py` 有 `GET /api/bookmarks`（列出）与 `POST /api/bookmarks`；若无列出端点则补。
**验收**
- 三态侧栏与原型一致；**Pro 态侧栏不含任何升级字样**（自动化断言）；未登录加入的稍后读在登录后出现在账户内。

### Epic E — Taxonomy + 管理后台（重点）
**数据模型（新 Alembic `0002_taxonomy.py`，L3 owned）**
- `taxonomy_categories`：`code`(PK,str64)、`label_en`、`label_zh`、`color_from`、`color_to`、`sort_order`(int)、`active`(bool)。
- `audiences`：`code`(PK,str64)、`label_en`、`label_zh`、`is_default`(bool)、`sort_order`(int)。
- `audience_categories`：`audience_code`(FK)、`category_code`(FK)、`position`(int)，PK(`audience_code`,`category_code`)。
- `users` 增列：`is_admin`(bool, default false)、`audience_code`(nullable, FK→audiences.code)。
- **种子数据**：迁移内插入默认分类与受众（对照原型 `DEFAULT_CATEGORIES` / `DEFAULT_AUDIENCES`），并设 `general` 为 `is_default`。
- `models.py` 增对应 ORM；`repository.py` 增读写方法（Memory 与 SQL 两实现，保持 stub 可跑）。
**后端接口**
- Reader API（`/api`，JWT）：
  - `GET /api/taxonomy` → `{categories:[{code,label,color_from,color_to}], audience:{code,label,categories:[code...]}}`（按**当前用户**的 `audience_code`，未登录/未设取 default）。供阅读端渲染 chips。
  - 管理（**新增 `require_admin` 依赖**，类似 `require_plan`）：
    - `POST /api/admin/categories`、`PATCH /api/admin/categories/{code}`、`DELETE /api/admin/categories/{code}`
    - `POST /api/admin/audiences`、`PATCH /api/admin/audiences/{code}`、`DELETE /api/admin/audiences/{code}`
    - `PUT /api/admin/audiences/{code}/categories`（设置成员与顺序，body: `{categories:[code...]}`）
  - 用户受众：`PATCH /api/me/audience`（body `{audience_code}`）。
- Public API（`/v1`，API Key）：新增 `GET /v1/taxonomy`（公共安全：categories + audiences 的 code/label，**不含**任何内部字段）；保留现有 `/v1/verticals` 向后兼容。
**前端**
- 新路由 `app/[locale]/admin/page.tsx`（**admin 门禁**：`is_admin` 否则 404/跳登录）。对照原型「管理后台」：
  - 分类管理：列表（色块/可编辑中文名/code/内容数/删除）+ 新增表单（code+名+配色）。
  - 受众管理：每受众卡片（可编辑名/key/删除 + 分类开关胶囊）+ 新增受众表单 + 重置默认。
  - 改动调用上面 admin 接口；保存后**实时刷新阅读端 taxonomy 消费**。
- 阅读端 `lib/taxonomy.ts`：`getTaxonomy()`；首页用它渲染领域 chips 与「受众」展示；受众切换在真实产品中通常由后端按用户决定（原型的前端"受众切换器"为演示，落地时改为**展示当前受众**，切换入口留给管理后台/用户设置）。
- 新分类**暂无内容**时，列表显示友好空态（对照原型）。
**验收**
- admin 增/删/改分类与受众落库并经 `GET /api/taxonomy` 反映到阅读端 chips；非 admin 访问 admin 接口/页面被拒；`/v1/taxonomy` 不泄漏非公共字段；迁移 upgrade/downgrade smoke 通过。

### Epic F — 开发者页（`app/[locale]/developers/page.tsx`）
- 把 `components/ApiKeyPanel.tsx` 从 `login` 迁来并增强：密钥列表（scope/RPM/日配额/今日用量/复制/撤销）+ 生成密钥。
- 文档区（静态，对照原型）：价值点、快速开始 `curl`、端点表、**字段契约/隐私边界**表（`base_analysis`/用户数据/非 COMPLETED 不出站）、MCP 一行接入、近 7 天用量图。
- 用量数据：新增 `GET /api/api-keys/usage`（读 `api_usage_daily`，近 7 天）。
- 导航新增「开发者」入口。
**验收**：开发者页可自助查看文档/密钥/用量；账户页不再承载 API 部分。

### Epic G — 订阅页（`app/[locale]/pricing/page.tsx`）
- Free×Pro 对比卡（对照原型）：清单含/不含项；价格读 `config`（`price_pro_*`）。
- 复用 `components/BillingPanel.tsx` 的 checkout（月/年/早鸟），按钮放对比卡内。
- 升级时机：从首页/详情/配额用尽处跳转此页。
**验收**：对比清晰；checkout 流程（sandbox）可走通。

### Epic H — 早报页打磨（`app/[locale]/brief/page.tsx`）
- "为什么是这几条"说明（基于评分阈值 + 受众）；每条加读时与质量；保留公共/个人（Pro）`BriefGate`。
- 邮箱订阅入口（前端表单 → 既有 brief/email 流程或占位）。
- 登录-Pro 显示"已按你的关注个性化"。
**验收**：早报有解释与读时；Pro 显示个性化提示。

---

## 5. 账户页与导航调整
- `app/[locale]/login/page.tsx` **瘦身**：仅保留 `LoginForm` + 基础资料/兴趣（`InterestOnboarding`）；移出 `BillingPanel`→订阅页、`ApiKeyPanel`→开发者页。
- 导航最终项：阅读 / 早报 / 开发者 / 订阅（+ 登录态头像菜单内的 管理后台 当 `is_admin`）。

---

## 6. L3 派生展示字段（关键，勿改 L2）
在 **L3 序列化层**（reader-api 的 feed/read 输出 + `public_contract` 视情况）补充，不回写 L2：
- `read_time_minutes`：估算。优先用 provider 提供的正文词数；否则 `max(1, round(words/200))`，无正文则用 summary 长度兜底。放工具函数 `codepick_l3/derive.py::estimate_read_minutes(content)`。
- `reason`（入选理由，EN/ZH）：**确定性**地由六维分生成，函数 `derive.py::pick_reason(scores, locale)`。规则示例：取最高 1–2 维 → 模板（如 `depth>=88 and impact>=88 → "深度与影响双高，适合做决策参考"`；`novelty 最高 → "新颖度高，适合快速了解趋势"`）。纯展示，不声称改动 L2 判断。
- `thumbnail`：`ContentSummary.thumbnail` 已是可选。无图时前端用**按来源/领域生成的渐变封面**（对照原型 `thumb()`：领域配色 + 来源缩写 + 领域标签），保证离线/无图也有视觉。可做成 `components/CoverThumb.tsx`。
- `paragraphs`（详情双语，可选）：若 provider/L2 提供分段 `[{en,zh}]` 则透传；否则前端回退用 `base_analysis`/`translations` 整段。
> 这些字段加入 `lib/api.ts` 的 `ContentSummary`/`ContentDetail` 类型；若进 `/v1` 必须确认是公共安全（`read_time_minutes`/`reason`/`thumbnail` 可公开；`paragraphs` 视为公共摘要级，勿含内部 `base_analysis` 深度内容）。

---

## 7. API 契约附录（新增/变更）

```
# Reader API（/api，JWT）
GET   /api/me                         -> { email, nickname, plan, locale, audience_code, is_admin }
PATCH /api/me/audience                <- { audience_code }            -> 200
GET   /api/taxonomy                   -> { categories:[{code,label,color_from,color_to}],
                                           audience:{code,label,categories:[code,...]} }
GET   /api/companion/quota            -> { used, limit, plan, unlimited:bool }
GET   /api/bookmarks                  -> { items:[{content_id, note, highlights}] }   # 若缺则补
GET   /api/api-keys/usage             -> { days:[{day, count}], window:7 }

# Admin（/api/admin，require_admin）
POST   /api/admin/categories          <- { code, label_en, label_zh, color_from, color_to }
PATCH  /api/admin/categories/{code}   <- { label_en?, label_zh?, color_from?, color_to?, active?, sort_order? }
DELETE /api/admin/categories/{code}   -> 200（并从所有 audience 移除）
POST   /api/admin/audiences           <- { code, label_en, label_zh }
PATCH  /api/admin/audiences/{code}    <- { label_en?, label_zh?, is_default?, sort_order? }
DELETE /api/admin/audiences/{code}    -> 200（默认受众不可删 / 至少保留一个）
PUT    /api/admin/audiences/{code}/categories <- { categories:[code,...] }  # 覆盖成员与顺序

# Public API（/v1，API Key）— 仅公共安全字段
GET   /v1/taxonomy                    -> { categories:[{code,label}], audiences:[{code,label}] }
```
- 鉴权：admin 端点用新依赖 `require_admin`（基于 `users.is_admin`）；返回 403 当非 admin、401 当无 JWT。
- 错误约定沿用现有风格（404 内容不存在；429 配额；403 计划/权限）。

---

## 8. 前端目录落点（新增/重写）

```
apps/reader-web/
  app/[locale]/
    page.tsx                 # 重写：Hero+筛选+头条+信息流+稍后读
    items/[id]/page.tsx      # 重写：封面+原文链接+双语+六维+伴读
    brief/page.tsx           # 打磨
    developers/page.tsx      # 新增（文档+控制台）
    pricing/page.tsx         # 新增（对比+checkout）
    admin/page.tsx           # 新增（admin 门禁；分类/受众管理）
    login/page.tsx           # 瘦身
  components/
    Header.tsx               # 重写（含 authSlot/账户菜单）
    Sidebar.tsx              # 新增（plan 感知三态）
    FeedFilters.tsx          # 新增（领域 chips + 排序）
    ContentCard.tsx          # 新增（封面/读时/理由/稍后读）
    CoverThumb.tsx           # 新增（渐变封面回退）
    CompanionChat.tsx        # 重写 CompanionWidget（对话式）
    ReadingActions.tsx       # 重写（态 + 登录提示）
    BilingualBody.tsx        # 新增（段落级三态）
    ScoreRing.tsx / ScoreExplainer.tsx
    SaveLaterButton.tsx      # 本地优先 + 登录同步
    AccountMenu.tsx
    admin/CategoryManager.tsx, AudienceManager.tsx
    ApiKeyPanel.tsx          # 迁到 developers + 用量图
  lib/
    api.ts                   # 扩展类型（read_time_minutes/reason/paragraphs）
    session.ts               # useSession + getMe
    taxonomy.ts              # getTaxonomy
    saved.ts                 # 本地稍后读 + 同步
```
> 客户端交互全部走 `addEventListener`/React 事件，**不用行内 `onclick`**（与原型一致，避免 CSP/沙箱屏蔽内联处理器）。

---

## 9. 测试要求（新增，且保持既有 108+26 全绿）

**后端 pytest（`services/...`/`tests`）**
- taxonomy：admin 增/删/改分类与受众落库；`GET /api/taxonomy` 按用户受众返回正确分类集合；删除分类级联从受众移除；默认受众保护。
- 权限：非 admin 调 `/api/admin/*` → 403；无 JWT → 401。
- `/v1/taxonomy`：仅含公共字段；与 MCP 一致（若 MCP 暴露 taxonomy）。
- companion 配额可见性：`/api/companion/quota` 返回 used/limit；Pro `unlimited:true` 且不被 429。
- 派生字段：`estimate_read_minutes` / `pick_reason` 单测（确定性）。
- `/api/me`、`/api/me/audience`、bookmarks 列表。
**前端 Playwright（`apps/reader-web/tests`）**
- 首页：筛选/排序/加载更多/稍后读(未登录本地)/Hero 关闭。
- 详情：双语三态、伴读多轮+预设、配额可见、原文链接。
- 登录态：未登录/Free/Pro 侧栏差异，**Pro 侧栏无升级文案**断言。
- 管理后台：增分类→出现在阅读端 chips；增受众→出现在受众展示；非 admin 不可见 admin 页。
- a11y：focus 可见、关键控件有可访问名。
**迁移**：`0002` upgrade/downgrade smoke 纳入 `l3_verify`。

---

## 10. 边界 / 风险
- **分页**：`/api/feed` 是 cursor 制，原型数字分页仅示意 → 落地用 cursor「加载更多」。
- **受众切换权属**：原型让前端切换受众是为演示；真实产品里用户所属受众由后端/账户决定，前端默认只**展示**当前受众，切换权交管理后台或用户设置（按需）。
- **稍后读 = bookmarks 复用**：未登录本地 → 登录合并；注意去重与冲突（以服务端为准）。
- **读时/理由是 L3 派生**：务必只在 L3 序列化层生成，严禁回写 provider / L2。
- **i18n 完整性**：新文案 EN/ZH 双份，勿留裸中文在仅 EN 路由。
- **不破坏公共边界**：任何进入 `/v1` 的新字段先过 `public_contract` 审查。
- **保持 stub 可跑**：所有新功能在 `L3_USE_STUB_L2=true` + 内存仓储下要能本地起与测试。

---

## 11. 完成定义（DoD）
1. `python scripts/l3_verify.py` → `L3 VERIFY: PASS`（backend pytest 全绿含新增，reader-web typecheck/build/Playwright 全绿含新增，迁移 smoke 通过）。
2. 五个里程碑 PR 合并，每个独立可回滚、互不破坏。
3. 视觉与交互对齐 `docs/L3-redesign-v2-preview.html`（深色模式、a11y、三态侧栏、对话式伴读、管理后台闭环）。
4. `docs/L3-completion-audit.md` 增补本期需求的证据行。
5. 管理后台增一个分类 + 配一个受众，能在阅读端「受众」对应 chips 中看到（端到端验证）。

---

### 附：原型与本计划的对应关系
| 原型区块 | 对应 Epic | 关键文件 |
|---|---|---|
| 顶栏/主题/语言/账户菜单 | A, D | `Header.tsx`, `AccountMenu.tsx`, `globals.css` |
| 首页 Hero + 筛选 + 信息流 + 稍后读 | B | `page.tsx`, `FeedFilters.tsx`, `ContentCard.tsx`, `SaveLaterButton.tsx` |
| 详情（封面/原文/双语/六维/对话伴读） | C | `items/[id]/page.tsx`, `BilingualBody.tsx`, `CompanionChat.tsx`, `ScoreRing.tsx` |
| 登录态自适应侧栏 | D | `Sidebar.tsx`, `lib/session.ts`, `lib/saved.ts` |
| 👥 受众 + 🛠 管理后台 | E | `admin/page.tsx`, `admin/*Manager.tsx`, `lib/taxonomy.ts`, `0002_taxonomy.py`, reader-api `taxonomy/admin` 路由 |
| 开发者页 | F | `developers/page.tsx`, `ApiKeyPanel.tsx` |
| 订阅对比页 | G | `pricing/page.tsx`, `BillingPanel.tsx` |
| 早报 | H | `brief/page.tsx` |
