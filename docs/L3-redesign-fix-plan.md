# CodePick L3 — Redesign 验收修复清单（M6，交付 Codex）

> 本文是对 `docs/L3-redesign-dev-plan.md`（M1–M5）开发成果验收后的**返工清单**。实现者没有对话上下文，请只依据本文 + 仓库现状。
> 视觉/交互参考仍是 `docs/L3-redesign-v2-preview.html`（单文件可交互原型）。

## 当前基线（2026-06-10 验收实测，不得回退）

`python scripts/l3_verify.py` → **L3 VERIFY: PASS**：
- 迁移冒烟：`0001` + `0002_taxonomy` upgrade/downgrade 往返通过（13 张表）
- 后端 pytest：**108 passed**（`tests/test_l3_contracts.py`）
- reader-web：typecheck ✅ / next build ✅（8 路由）/ Playwright **26 passed**（13 用例 × chromium+mobile）

注意：`scripts/l3_verify.py` 第 ~66 行的超时兜底判断硬编码 `ok_count >= 26 or "26 passed"`。新增 Playwright 用例后请把该阈值同步更新（或改为读取 `>= N passed` 的通用判断），避免兜底逻辑失真。

## 已验收通过、本轮不要动的部分

- 后端 taxonomy 全套：`db/alembic/versions/0002_taxonomy.py`、`codepick_l3/repository.py`（memory+SQL 双实现）、`reader_api/routers/{taxonomy,admin,me}.py`、`public_api` 的 `GET /v1/taxonomy` 公共字段过滤。
- 详情页双语 `BilingualBody`、封面 `CoverThumb`、读时/理由派生（`lib/api.ts` 的 `enrichSummary`）、三态 `Sidebar` 骨架、`ThemeToggle`、页面拆分（developers/pricing/admin 路由）。
- 全部既有测试（108 后端 + 26 E2E）。

---

## 修复项（按优先级；每项含「现状 → 期望 → 验收」）

### P0-1 首页筛选/排序不生效（最高优先）

**现状**：`apps/reader-web/app/[locale]/page.tsx` 的 `Home({ params })` 不接收 `searchParams`；`lib/api.ts` 的 `getFeed()` 无参数、请求 `/api/feed` 不带 query。`components/FeedFilters.tsx` 渲染的 `?vertical=xx` / `?sort=xx` 链接点了**列表不变**，且「全部」chip 永远高亮（`chip-active` 写死）。

**期望**：
1. `Home({ params, searchParams })` 读取 `searchParams.vertical` / `searchParams.sort`（sort 合法值：`recommended|published_at|score`，`recommended` 映射后端默认或 `score`，自行决定并保持一致）。
2. `getFeed(options?: { vertical?: string; sort?: string; cursor?: string; limit?: number })` 把参数拼到 `/api/feed`（后端已支持 `vertical/sort/cursor/limit`，无需改后端）。
3. `FeedFilters` 接收当前 `vertical/sort`，正确高亮当前选中 chip 与排序段（不能永远高亮「全部」）；链接保留其他参数（切 vertical 不丢 sort，反之亦然）。
4. **加载更多**：`/api/feed` 返回 `next_cursor`。首屏 SSR 渲染第一页；新增一个客户端组件（如 `components/LoadMore.tsx`）持有 `next_cursor`，点击后用 `NEXT_PUBLIC_READER_API_BASE` 直接拉下一页并 append（沿用仓库现有「API 失败回退本地」的容错风格：失败时按钮显示不可用提示即可，不崩）。

**验收（新增 Playwright）**：
- 访问 `/en?vertical=ai` 时列表仅含 `ai` 内容、`ai` chip 高亮；
- 切 `?sort=score` 后首条卡片质量分为最大值；
- stub 数据不足以翻页时，可在测试中 `page.route` mock `/api/feed` 返回带 `next_cursor` 的两页数据，断言点击「加载更多」后卡片数增加。

### P0-2 阅读端未消费 `/api/taxonomy`（打通「后台改分类 → 阅读端可见」）

**现状**：`FeedFilters` 的分类 chips 来自 feed 内容里 `vertical` 原始 code 去重（显示 `ai`/`infra` 这类英文 code），没调 `/api/taxonomy`，不显示后台配置的本地化 label，也不按用户受众过滤。导致 dev-plan DoD #5（管理后台加分类→阅读端 chips 可见）端到端断链。

**后端已就绪，直接消费即可**。`GET /api/taxonomy`（匿名可访问，匿名返回默认受众；带 JWT 按用户 `audience_code`）返回：

```json
{
  "categories": [
    { "code": "ai", "label": "AI", "label_en": "AI", "label_zh": "AI",
      "color_from": "#4f46e5", "color_to": "#14b8a6", "sort_order": 0, "active": true }
  ],
  "audience": { "code": "general", "label": "...", "categories": ["ai", "..."] },
  "audiences": [ { "code": "general", "label": "..." } ]
}
```
（`label` 已按 locale 本地化；`categories` 已按受众过滤并排序。）

**期望**：
1. 新增 `apps/reader-web/lib/taxonomy.ts`：`getTaxonomy(locale, token?)` 调 `/api/taxonomy`（服务端 fetch 带 `next: { revalidate: 60 }`；失败回退到 feed verticals 去重的现状逻辑——保持 stub/离线可用）。
2. 首页用 taxonomy 渲染 chips：显示 `label`（zh 路由显示中文），`href` 仍用 `?vertical=<code>`；chips 顺序按 `sort_order`。
3. 内容里存在但 taxonomy 没有的 vertical：不展示该 chip（taxonomy 是权威）；反之 taxonomy 有但暂无内容的分类照常展示，点进去空列表给友好空态文案（中英双语）。

**验收（新增 Playwright）**：mock `/api/taxonomy` 返回含自定义分类（如 `{code:"ops",label:"运营"}`）→ 断言 `/zh` 首页出现「运营」chip；点击后请求带 `vertical=ops`。

### P1-3 伴读配额可见性前后端没接上

**现状**：`components/CompanionWidget.tsx` 读响应头 `X-Companion-Remaining` / `X-Companion-Limit`，但 `services/reader-api/reader_api/routers/companion.py` **从未发送**这两个头 → 配额永远显示写死的 "Free: 5/day"。后端已有 `GET /api/companion/quota`（返回 `{used, limit, plan, unlimited}`，在 `routers/me.py`），前端没用。Pro 无限在前端无任何体现。

**期望（两端都做，彻底闭环）**：
1. 后端 `companion.py`：在 `StreamingResponse` 上设置响应头——`X-Companion-Limit: <companion_free_daily>`、`X-Companion-Remaining: <max(0, limit-count)>`；Pro 用户加 `X-Companion-Unlimited: true`（Remaining 可发 `-1`）。注意 `count` 已在现有代码里算好，不要改变 429 行为与计数时序（有测试锁定）。
2. 前端 `CompanionWidget`：挂载时调 `GET /api/companion/quota` 初始化显示（无 token/失败时回退现状文案）；每次提问后用响应头更新。`unlimited:true` 时显示「Pro · 无限」（EN: "Pro · Unlimited"），不显示剩余次数。
3. 顺手修一个小体验问题：预设追问按钮目前只是把文案填进输入框，请改为**填入并直接提交**（复用同一提交函数）。

**验收**：
- 新增后端测试：断言 `/api/companion` 响应包含上述头，free 用户 Remaining 递减、pro 用户 `X-Companion-Unlimited: true`；
- 新增/扩展 Playwright：mock `/api/companion/quota` 返回 `{used:2,limit:5,unlimited:false}` → 断言界面显示 `3/5` 或等价文案；mock `unlimited:true` → 显示 Pro 无限。

### P1-4 管理后台从「壳层」补成可用 CRUD

**现状**：`apps/reader-web/components/admin/AdminTaxonomyPanel.tsx` 只有「新增分类」「新增受众」两个表单；无编辑/删除/受众-分类勾选；新建受众时自动把**全部**分类塞给它；页面副标题自己写着"完整 CRUD 会在 Taxonomy 里程碑接入"；`app/[locale]/admin/page.tsx` 无 `is_admin` 前端门禁（任何人可打开页面，仅靠 API 403 兜底）。

**后端已就绪**（全部存在，勿改契约）：
- `GET /api/admin/taxonomy`（categories 含 inactive + audiences）
- `POST/PATCH/DELETE /api/admin/categories[/{code}]`（DELETE 已级联从受众移除）
- `POST/PATCH/DELETE /api/admin/audiences[/{code}]`（默认受众/最后一个受众删除会 400）
- `PUT /api/admin/audiences/{code}/categories`（body `{categories:[code...]}`，覆盖式）

**期望**：
1. **页面门禁**：admin 页挂载时调 `GET /api/me`，`is_admin !== true` 显示「无权限」并引导回首页（不渲染管理 UI）。保留无后端时的本地演示回退（`codepick_is_admin` localStorage），与仓库其他组件容错风格一致。
2. **分类管理**：列表每行显示色块（`color_from→color_to` 渐变）、中英文名（可编辑，blur 或保存按钮触发 `PATCH`）、code、删除按钮（触发 `DELETE`，删完刷新）。新增表单补一个简单配色选择（给 4–8 个预设渐变即可）+ 中/英文名两个输入框（当前只有 code，label 是从 code 转的）。
3. **受众管理**：每个受众卡片内列出全部分类的**勾选胶囊**（当前受众包含的高亮），点击切换后 `PUT .../categories` 覆盖保存；受众名可编辑（PATCH）；删除按钮（对 400 给出「默认/最后一个受众不可删」提示）。新建受众不再自动塞全部分类（默认空集合或前 3 个，二选一并保持测试一致）。
4. 去掉页面副标题里"壳层/里程碑"占位文案，换成正式描述（中英双语）。

**验收（扩展现有 admin Playwright 用例）**：mock admin API → 断言：编辑分类名发出 PATCH；删除发出 DELETE；勾选受众分类发出 PUT 且 body 正确；非 admin（`/api/me` 返回 `is_admin:false`）看到无权限提示而非管理表单。

### P2-5 登录态数据接真（/api/me、兴趣、稍后读同步）

**现状**：
- `components/AccountMenu.tsx` 的 `localSession()` 硬编码 `email: "dev@example.com"`，plan/is_admin 全靠 localStorage，没调后端已有的 `GET /api/me`。
- `components/Sidebar.tsx` 「关注领域」是写死文案（"AI、工程、数据"），没调已有的 `GET /api/interests`。
- 稍后读（`cp_saved`）纯本地，登录后不同步——dev-plan Epic D 要求「登录后合并到 `/api/bookmarks`」未做。

**期望**：
1. 新增 `apps/reader-web/lib/session.ts`：`getMe(token)` 调 `GET /api/me`，失败回退 localStorage 演示态（保持 Playwright 现有用例可过）。`AccountMenu` 与 `Sidebar` 改用它（真实 email/plan/is_admin/audience_code）。
2. `Sidebar` 关注领域改调 `GET /api/interests`（失败回退现有文案）。
3. **稍后读同步**：登录成功后（`LoginForm` 写入 token 处）读取 `cp_saved`，逐条 `POST /api/bookmarks`（body `{content_id, note:"saved from reader", highlights:[]}`），全部成功后清空本地并提示「已同步 N 条稍后读」；任一失败保留本地不清（幂等：服务端 bookmarks 以 `(user_id, content_id)` 为主键，重复 POST 安全）。
4. 首页 Hero（`hero-band`）：加关闭按钮（`localStorage('cp_hero_dismissed')`），有 token 时不渲染。

**验收**：Playwright——mock `/api/me` 返回 `{email:"maya@x.com", plan:"pro", is_admin:false}` → 账户菜单显示该 email 与 Pro；预置 `cp_saved=["cp-001"]` 后登录 → 断言发出 `POST /api/bookmarks` 且 body.content_id="cp-001"；关闭 Hero 刷新后不再出现。

### P2-6 开发者页补用量端点与展示

**现状**：dev-plan Epic F 要求的 `GET /api/api-keys/usage` 未实现；developers 页无近 7 天用量展示。

**期望**：
1. 后端 `reader_api/routers/api_keys.py` 新增 `GET /api-keys/usage`（JWT）：聚合当前用户全部 key 近 7 天 `api_usage_daily`，返回 `{days:[{day:"YYYY-MM-DD",count:int}...7 条（缺日补 0）], window:7}`。memory 与 SQL 两种 quota/repo 后端都要支持（参考 `usage.py` 现有读写路径）。
2. developers 页加一个简单 7 日柱状图（纯 CSS div 高度即可，参考原型 `.chart`；无数据全 0 也要渲染）。

**验收**：后端测试——种入两天用量后断言返回 7 条且对应日 count 正确、JWT 缺失 401；Playwright——mock 返回后断言图表渲染 7 列。

---

## 全局约束（与 dev-plan 相同，重申）

1. **L2 只读**：不得改 provider 返回的内容与评分；派生展示字段只在 L3 层。
2. **公共边界**：本轮无字段进 `/v1`；不得在 `/v1`/MCP 暴露 `label_en/label_zh/color_*` 之外新增内部字段（现有 `/v1/taxonomy` 只出 `{code,label}`，保持）。
3. **stub 可跑**：所有改动在 `L3_USE_STUB_L2=true` + 内存仓储下可本地运行与测试；前端调用失败一律优雅回退（沿用现有模式），Playwright 不依赖真实后端。
4. **i18n**：所有新增用户可见文案 EN/ZH 双份。
5. **不回退基线**：完成后 `python scripts/l3_verify.py` 必须 `L3 VERIFY: PASS`，后端 ≥108 passed、Playwright ≥26 passed（新增用例计入；记得同步 `l3_verify.py` 的兜底阈值）。
6. 完成后在 `docs/L3-completion-audit.md` 的「L3 Redesign Evidence」段补一行 M6 修复证据。

## 建议提交拆分

- PR-1：P0-1 + P0-2（首页筛选/排序/加载更多 + taxonomy 消费）— 一起改 `page.tsx/FeedFilters/lib`，互相耦合
- PR-2：P1-3（伴读配额，后端响应头 + 前端显示）
- PR-3：P1-4（管理后台 CRUD + 门禁）
- PR-4：P2-5 + P2-6（登录态接真 + 用量端点）

每个 PR 独立全绿，可独立回滚。
