# CodePick L3

[2026-09-12 当前验证与剩余工作](docs/2026-09-12-continuation.md) · [平台项目进度](../codepick-docs/PROJECT_STATUS.md)

[异地开发指南](DEVELOPMENT.md) · [平台总文档与关联仓库](https://github.com/jayson2hu/codepick-docs)

L3 implements the reader application and distribution layer with strict separation from L2. During development it uses `StubContentReadProvider`, sandbox billing, and mock email delivery.

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

The web app can run without the API during local UI checks because it falls back to the same stub fixture shape. In full local mode, start `reader-api` and set `READER_API_BASE`.

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

MCP smoke:

```bash
make mcp-smoke
```

The MCP wrapper uses the same public item serializer as `/v1` and exposes `today`, `search`, and `item` tool contracts without private recommendation context.

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

## Sprint Status

- S1 foundation/display: scaffold, provider stub, public feed, detail, pagination contract, and backend tests.
- S2 account/personalization: JWT login, subscription-backed `require_plan`, interests, follows, bookmarks, recommendations, and event tracking.
- S3 companion/brief: companion quota, public/personal brief generation hooks, mock email delivery, and repository-backed brief persistence.
- S3 worker runtime: Arq-compatible `WorkerSettings` and Redis env mapping.
- S4 billing: sandbox checkout, signed webhook subscription sync, USD pricing invariants, and Paddle production switch path.
- S5 API/MCP/i18n: `/v1` primitives, API key lifecycle and quota checks, MCP `today/search/item` wrappers, shared public field filtering, bilingual UI routes, and SEO metadata.

Remaining work includes real authentication and account isolation, browser/API integration, the L2 HTTP service, official Paddle checkout/webhook handling, MCP protocol transport, and dependency upgrades, in addition to PostgreSQL, Redis/Arq, and email integration. The current stub/sandbox paths do not become production-ready through configuration alone. See the dated continuation record above for current evidence.

