# CodePick L3

[2026-09-12 当前验证与剩余工作](docs/2026-09-12-continuation.md) · [平台项目进度](../codepick-docs/PROJECT_STATUS.md)

[异地开发指南](DEVELOPMENT.md) · [平台总文档与关联仓库](https://github.com/jayson2hu/codepick-docs)

L3 implements the reader application and distribution layer with strict separation from L2. During development it uses `StubContentReadProvider`, sandbox billing, and mock email delivery.

## Real-source reading preview (2026-09-17)

[This iteration](docs/2026-09-17-real-content-preview.md) · [Reader UX](apps/reader-web/UX_REDESIGN.md) · [Private preview / remote access](../codepick-docs/REAL_CONTENT_PREVIEW.md)

The private real-source preview disables the L2 stub and demo fallback. Feed search runs upstream before pagination. Reader and Public API roots redirect to `/docs`; the website root redirects to `/zh`. Source/analysis provenance and unavailable translations are explicit. Anonymous saves belong to the current browser; account actions report errors instead of pretending success. Backend acceptance: 166 tests plus smoke, development preflight and isolated SQLite migration round-trip passed.

## Layout

- `apps/reader-web`: Next.js App Router reader app with i18n routes.
- `services/reader-api`: internal BFF under `/api`, protected with JWT.
- `services/public-api`: external API under `/v1`, protected with API key plus quota.
- `services/shared/codepick_l3`: shared domain, provider abstraction, auth, gating, billing, public contracts, and brief logic.
- `workers/briefs`: public and personal daily brief jobs.
- `services/mcp-server`: MCP-facing tool wrappers for public `today/search/item` contracts.
- `db/alembic/versions`: L3-owned table migration.
- `.github/workflows/l3-ci.yml`: backend smoke and reader-web typecheck/E2E CI.

## Specification Artifacts

The required L3 HTML package lives under `docs/`:

- `L3-应用与分发-产品文档.html`: product matrix, Free/Pro policy, pricing, north-star metric, and independent-development boundary.
- `L3-应用与分发-架构设计.html`: service topology, trust boundaries, data ownership, runtime switches, and verification strategy.
- `L3-开发Plan-详尽版.html`: E0-E9 feature plan, acceptance criteria, and self-test checklist.
- `L3-实施手册-交付包.html`: scaffold, interface contracts, configuration, smoke checks, and DoD.
- `L3-sprint-handoff.md`: sprint-level handoff record with implemented features, self-test evidence, coverage, and residual integration work.
- `L3-final-integration-checklist.md`: final go/no-go checklist for real L2, PostgreSQL, Redis/Arq, email, and Paddle integration.
- `L3-completion-audit.md`: requirement-by-requirement evidence for the independent L3 deliverable and the final integration gate.
## Commands

```bash
python -m pytest -c pytest.ini tests
python scripts/l3_smoke.py
python scripts/l3_migration_smoke.py
python scripts/l3_clean.py
python scripts/l3_preflight.py
python scripts/l3_preflight.py --final
python scripts/l3_final_probe.py
python scripts/l3_verify.py
make l3-smoke
make l3-migration-smoke
make l3-clean
make l3-preflight
make l3-preflight-final
make l3-final-probe
make l3-verify
```

`make l3-smoke` runs the same Python smoke runner. On Windows without `make`, call `python scripts/l3_smoke.py`. Success prints `L3 PIPELINE: PASS`.

`make l3-migration-smoke` runs Alembic upgrade/head then downgrade/base against a disposable SQLite database by default, proving the migration command path and all L3-owned tables round-trip. Set `L3_MIGRATION_SMOKE_DATABASE_URL` to run the same check against a real PostgreSQL integration database.

`make l3-clean` removes generated pytest, Next.js, Playwright, TypeScript, egg-info, and `__pycache__` artifacts. On Windows without `make`, call `python scripts/l3_clean.py`.

`make l3-preflight` validates independent-development configuration. `make l3-preflight-final` fails fast unless final integration switches are explicit: real L2 URL, SQLAlchemy/PostgreSQL, SQLAlchemy quota, production Paddle config, non-default secrets, Resend/SES config, Redis settings, and fixed USD pricing. It validates configuration only.

`make l3-final-probe` runs live final integration checks in the target environment after `python scripts/l3_preflight.py --final`: HTTPS `L2_BASE_URL` list/get through `ContentReadProvider`, PostgreSQL `DATABASE_URL` connectivity and L3-owned tables, SQLAlchemy quota tables, Redis/Arq ping, Resend/SES client configuration, and production Paddle config. It is non-destructive by default; add `--send-test-email ops@example.com` to send a real provider test brief and `--enqueue-brief` to enqueue a public brief job.

`python scripts/l3_verify.py` is the cross-platform full handoff gate. `make l3-verify` delegates to it. It mirrors CI: dev preflight, Alembic migration smoke, backend L3 smoke, reader-web typecheck, production build, Playwright E2E, then cleanup. Success prints `L3 VERIFY: PASS`.

Frontend:

```bash
cd apps/reader-web
npm ci
npm run typecheck
npm run build
npm run test:e2e
```

The web app can run without the API during explicit demo checks when
`READER_USE_DEMO_FALLBACK=true`. In M2 real mode, set it to `false`; failed
Reader/L2 requests then render the retryable error boundary and never silently
replace real content with the demo fixture.

Local infrastructure:

```bash
cp .env.example .env
docker compose up -d postgres redis
docker compose ps postgres redis
alembic -c db/alembic.ini upgrade head
python scripts/run_reader_api.py
python scripts/run_public_api.py
python scripts/run_mcp_server.py
```

`alembic` uses `DATABASE_URL` when it is set, matching the SQLAlchemy runtime switch used by Reader API, Public API, workers, and quota storage. Without `DATABASE_URL`, it falls back to the local Postgres URL in `db/alembic.ini`.

`docker-compose.yml` includes Postgres `pg_isready` and Redis `redis-cli ping` health checks. Use `make infra-status` before running migrations or workers when debugging local infra startup.

Reader API runs on `127.0.0.1:8000`; Public API runs on `127.0.0.1:8001`. Use `X-API-Key: cp_test_key` for local `/v1` smoke calls.
The Public API launcher also accepts `PUBLIC_API_HOST`, `PUBLIC_API_PORT`, and
`PUBLIC_API_RELOAD`; reload defaults to false so local acceptance can use an
isolated deterministic process.

MCP smoke:

```bash
make mcp-smoke
```

The MCP wrapper uses the same public item serializer as `/v1` and exposes `today`, `search`, and `item` tool contracts without private recommendation context.
Public API `GET /v1/search?q=...&cursor=...&limit=...` and MCP `search` both
send the query to the active content provider. With real L2 enabled, filtering
happens in L2 before cursor pagination; neither surface performs page-local
post-filtering.

Brief worker:

```bash
make brief-worker
make brief-enqueue-public
python scripts/enqueue_brief.py --type personal --user-id 1 --email pro@example.com
```

The Arq worker exposes both public and personal brief jobs and schedules the public daily brief via `BRIEF_PUBLIC_CRON_HOUR_UTC` / `BRIEF_PUBLIC_CRON_MINUTE_UTC`. Set `BRIEF_RUN_AT_STARTUP=true` only when you want the worker to emit a public brief immediately on boot.

Readiness endpoints expose the active L3 runtime switches without crossing service boundaries:

```bash
curl http://127.0.0.1:8000/api/ready
curl -H "X-API-Key: cp_test_key" http://127.0.0.1:8001/v1/ready
```

The default independent-development state should report `status=ready` with stub L2, memory repository/quota, sandbox billing, and mock email. During final integration, `status=degraded` identifies missing real L2, SQLAlchemy/PostgreSQL, email, billing, or worker configuration before traffic is switched.

## Configuration

The implementation defaults to independent development settings:

```env
L3_USE_STUB_L2=true
JWT_SECRET=dev-secret
PADDLE_WEBHOOK_SECRET=dev-webhook-secret
PRICE_PRO_MONTH_USD=8
PRICE_PRO_YEAR_USD=79
PRICE_EARLYBIRD_USD=4.9
COMPANION_FREE_DAILY=5
API_RATE_FREE_RPM=20
API_QUOTA_FREE_DAY=200
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en,zh
```

Switching to real L2 is intentionally isolated behind `ContentReadProvider`. Set `L3_USE_STUB_L2=false`, `L2_BASE_URL`, and optional `L2_API_KEY` to use the HTTP provider.

For local M2 integration, start Reader API on a loopback-only port:

```bash
L3_USE_STUB_L2=false \
L2_BASE_URL=http://127.0.0.1:8200 \
READER_API_HOST=127.0.0.1 \
READER_API_PORT=8100 \
.venv/bin/python scripts/run_reader_api.py
```

Then start reader-web with the same-origin proxy and demo fallback disabled:

```bash
cd apps/reader-web
READER_API_BASE=http://127.0.0.1:8100 \
READER_API_PROXY_TARGET=http://127.0.0.1:8100 \
READER_USE_DEMO_FALLBACK=false \
NEXT_TELEMETRY_DISABLED=1 \
npm run dev -- --hostname 127.0.0.1 --port 3200
```

The L2 HTTP provider maps a missing detail item to L3 404. Invalid cursors and
other L2 400 responses become L3 400 `invalid_request`; L2 401/403 or missing
provider configuration become non-retryable 503 `l2_configuration_error`.
Network failures, timeouts, malformed upstream schemas, list-endpoint 404, and
L2 5xx responses become retryable L3 503 `l2_unavailable` with `Retry-After: 2`.
`/api/*` is proxied by Next.js, so browsers do not require cross-origin access in
the normal local topology.

Set `L3_REPOSITORY_BACKEND=sqlalchemy` with `DATABASE_URL` when L3-owned state should be persisted through SQLAlchemy/PostgreSQL. Set `L3_QUOTA_BACKEND=sqlalchemy` when `/v1` API key usage should be enforced through `api_keys` and `api_usage_daily` instead of the local in-memory development store.

## Integration Switches

Defaults keep L3 independently runnable:

```env
L3_USE_STUB_L2=true
EMAIL_PROVIDER=mock
BILLING_ENVIRONMENT=sandbox
```

Final integration switches are explicit:

```env
L3_USE_STUB_L2=false
L2_BASE_URL=https://l2.example
L2_API_KEY=...
EMAIL_PROVIDER=resend
EMAIL_FROM=CodePick <briefs@codepick.dev>
RESEND_API_KEY=...
RESEND_API_URL=https://api.resend.com/emails
BILLING_ENVIRONMENT=production
PADDLE_CHECKOUT_BASE_URL=https://checkout.paddle.com
ARQ_REDIS_HOST=127.0.0.1
ARQ_REDIS_PORT=6379
```

If `L3_USE_STUB_L2=false` is set without `L2_BASE_URL`, startup paths fail fast instead of silently reading fixtures. `/v1` remains on API key auth and exposes only trimmed public content fields.

Email defaults to the mock delivery sink for independent development. `EMAIL_PROVIDER=resend` posts daily brief payloads to `RESEND_API_URL` with `RESEND_API_KEY`; `EMAIL_PROVIDER=ses` uses AWS SES through `boto3` and requires `SES_REGION` plus normal AWS credentials in the runtime environment.

Billing webhooks must be signed with `X-Paddle-Signature` before any subscription state changes. The webhook handler accepts the local sandbox shape (`{"user_id": 1, "event": "subscription.activated"}`) and Paddle-style payloads with `event_type` plus `data.custom_data.user_id`. Activation and transaction completion promote the user to Pro; canceled, paused, or past-due subscriptions downgrade to Free.

## Public API Keys

Signed-in Reader API users can manage distribution keys through the internal JWT boundary:

```bash
POST /api/api-keys
GET /api/api-keys
DELETE /api/api-keys/{prefix}
```

The raw key is returned only on creation. Public distribution calls use `X-API-Key` against `/v1/*`; revoked keys are rejected before content is read.

Public API content and taxonomy primitives return quota context at the response envelope:

```json
{
  "items": [],
  "next_cursor": null,
  "quota": { "daily": 200, "rate_limit_rpm": 20 }
}
```

`GET /v1/items/{id}` uses `{ "item": { ...public fields... }, "quota": { ... } }` so quota metadata never expands the public item field set. `/v1/ready` authenticates with `X-API-Key` but does not consume daily quota or RPM.

Search is server-side and cursor-stable: `q` is limited to 200 characters and is
applied to title/summary before pagination. Public API and MCP use the same provider
query. Provider failures are never replaced with stub content when
`L3_USE_STUB_L2=false`.

## Sprint Status

- S1 foundation/display: scaffold, provider stub, public feed, detail, pagination contract, and backend tests.
- S2 account/personalization: JWT login, subscription-backed `require_plan`, interests, follows, bookmarks, recommendations, and event tracking.
- S3 companion/brief: companion quota, public/personal brief generation hooks, mock email delivery, and repository-backed brief persistence.
- S3 worker runtime: Arq-compatible `WorkerSettings` and Redis env mapping.
- S4 billing: sandbox checkout, signed webhook subscription sync, USD pricing invariants, and Paddle production switch path.
- S5 API/MCP/i18n: `/v1` primitives, API key lifecycle and quota checks, MCP `today/search/item` wrappers, shared public field filtering, bilingual UI routes, and SEO metadata.

M2 browser/API integration and the L2 HTTP service are now implemented and verified
locally without API mocks against the retained M1 SQLite result. M3 adds persistent
per-user account isolation, authentication failure boundaries, and the secure
frontend dependency baseline. Public API/MCP search now uses L2-side filtering
before pagination and has explicit request, configuration, missing-item, and
retryable-upstream error boundaries. Remaining work includes a real identity provider,
official Paddle checkout/webhook handling, MCP protocol transport, and full
PostgreSQL/Redis/Arq/email/real-model integration. The current development and
sandbox paths do not become production-ready through configuration alone. See the
platform M2 and M3 records for current evidence.

## M3 Account Isolation And Secure Frontend Baseline

The development email login no longer maps every address to user 1. In
`L3_AUTH_LOGIN_MODE=development`, normalized email addresses resolve to stable,
distinct users in both the memory and SQLAlchemy repositories. Interests, follows,
bookmarks, reading metrics, subscriptions, API keys, revocation, and usage are
scoped by the authenticated user ID.

`L3_AUTH_LOGIN_MODE=external` disables `POST /api/auth/login`; this is the
required final-preflight setting so a production-like configuration cannot accept
an arbitrary email as verified. It is an integration boundary, not a claim that a
real identity provider has been implemented. A real OIDC/magic-link provider and
credential lifecycle remain outside this milestone.

JWT decoding returns 401 for expired, tampered, malformed, or incomplete bearer
tokens. Final preflight now includes an explicit auth check:

```sh
L3_AUTH_LOGIN_MODE=external python scripts/l3_preflight.py --final
```

Reader Web now uses Next.js 16.3.5, PostCSS 8.5.28, and Playwright 1.63.0.
`npm audit --audit-level=low` reports zero vulnerabilities. Dynamic route
`params` and `searchParams` use the Next 16 async contract. For restricted
Ubuntu hosts, Playwright may use an already installed browser without changing the
default behavior:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome-headless-shell npm run test:e2e
```

M3 acceptance evidence is recorded in the platform
`M3_ACCOUNT_ISOLATION.md` document. PostgreSQL validation used a disposable
database bound only to localhost; real authentication, production billing, real
email, and production databases were not contacted.
