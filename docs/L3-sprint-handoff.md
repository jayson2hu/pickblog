# L3 Sprint Handoff

This file captures the sprint-level delivery notes required by the L3 plan. The workspace is not currently a Git repository, so these notes serve as the durable commit-equivalent handoff record for implemented features, self-test evidence, coverage, and remaining work.

## Current Verification

- Full handoff gate: `python scripts/l3_verify.py` -> `L3 VERIFY: PASS`
- Backend contracts: `127 passed` (previous independent baseline: `126 passed`)
- Reader Web Playwright: `26 passed`
- Migration smoke: `L3 MIGRATION: PASS`
- Sprint smoke: `L3 PIPELINE: PASS`

## S1 Foundation And Display

- Implemented features: F0.1-F0.4, F1.1-F1.2, F2.1-F2.3.
- Scope: Next.js Reader Web, Reader API, Public API, Alembic migration, `ContentReadProvider`, stub fixtures, public feed, bilingual detail, pagination, SEO baseline.
- Self-test evidence: backend contract tests cover protected route 401, public API key 401, migration upgrade/downgrade, stub provider, pagination, public schema trimming, and completed-only read paths; Playwright covers public picks, language switch, detail analysis, and SEO JSON-LD.
- Coverage/evidence: included in `108 passed` backend contracts and `26 passed` Playwright E2E.
- Remaining work: final integration must point `L3_USE_STUB_L2=false` at real HTTPS L2 and validate live provider responses.

## S2 Account And Personalization

- Implemented features: F3.1-F3.2, F4.1-F4.4.
- Scope: JWT login, subscription-backed `require_plan`, interests, follows, bookmarks, recommendations, behavior events, and north-star metric.
- Self-test evidence: backend tests cover forged plan rejection, centralized plan checks, interest validation, bookmarks, recommendations, SQLAlchemy persistence, completed-only mutations, event type validation, and north-star anti-metrics; Playwright covers login, interest save, recommendations, click tracking, deep-read, bookmark, and not-interested actions.
- Coverage/evidence: included in `108 passed` backend contracts and `26 passed` Playwright E2E.
- Remaining work: final integration should confirm behavior events flow into production analytics without adding reading-time or DAU optimization.

## S3 Companion And Brief

- Implemented features: F5.1-F5.2, F6.1-F6.3.
- Scope: AI companion streaming, free quota, Pro bypass, public/personal brief generation, brief persistence, mock email delivery, and Arq-compatible worker jobs.
- Self-test evidence: backend tests cover companion SSE contract, quota enforcement, non-completed rejection before usage, brief deduplication, completed-only brief filtering, worker job persistence, mock email delivery, and Redis env mapping.
- Coverage/evidence: included in `108 passed` backend contracts and `L3 PIPELINE: PASS`.
- Remaining work: final integration must run workers against real Redis/Arq and send real Resend/SES email in the target environment.

## S4 Commercialization

- Implemented features: F7.1-F7.2.
- Scope: sandbox checkout, USD pricing invariants, Paddle-style signed webhook handling, subscription promotion/downgrade, production switch readiness.
- Self-test evidence: backend tests cover supported checkout cadences, unknown cadence rejection, webhook signature verification, bad signature rejection, activation, transaction completion, cancellation, and fixed USD prices `$8`, `$79`, `$4.9`.
- Coverage/evidence: included in `108 passed` backend contracts.
- Remaining work: final integration must verify real Paddle production checkout and webhook delivery with non-default secrets.

## S5 API, MCP, I18n, And SEO

- Implemented features: F8.1-F8.3, F9.1-F9.2.
- Scope: public `/v1` API, API key lifecycle, rate limit/quota, MCP wrappers, shared public serializer, quota envelope, readiness auth, bilingual UI, Chinese copy validation, sitemap, and SEO metadata.
- Self-test evidence: backend tests cover API key lifecycle, read-scope enforcement, ready auth without quota consumption, daily quota, RPM limit, public item field set, taxonomy quota, completed-only `/v1` and MCP filtering, MCP smoke, UTF-8 copy checks, and final checklist coverage; Playwright covers English/Chinese routes, localized controls, sitemap, and detail metadata.
- Coverage/evidence: included in `127 passed` backend contracts and `26 passed` Playwright E2E.
- Search now pushes `q` into the shared provider before pagination for both
  `/v1/search` and MCP `search`. Tests cover cursor-stable results, Public/MCP
  consistency, query length, invalid cursors, and HTTP query forwarding.
- Provider failures distinguish invalid requests (400), missing detail items (404),
  non-retryable L2 configuration/authentication failures (503), and retryable
  network, schema, list-404, or upstream-5xx failures (503 with `Retry-After: 2`).
- Remaining work: final integration must validate `/v1` and MCP against production API key storage and real L2 content.

## Final Integration Residuals

- Target/production PostgreSQL `DATABASE_URL` with SQLAlchemy repository and quota backends.
- Real HTTPS L2 provider endpoint and optional `L2_API_KEY`.
- Redis/Arq worker runtime using explicit `ARQ_REDIS_HOST` and `ARQ_REDIS_PORT`.
- Resend or SES credentials and sender identity.
- Paddle production checkout URL and signed webhook delivery.
- Go/no-go execution using `docs/L3-final-integration-checklist.md`.

## M3 Account Isolation And Dependency Security

- Development login resolves normalized email to stable, distinct memory or
  SQLAlchemy users instead of hard-coding user 1.
- User-visible interests, follows, bookmarks, reading-event metrics,
  subscriptions, API keys, revocation, and usage are user-scoped.
- Expired, tampered, malformed, and incomplete JWTs return 401.
- `L3_AUTH_LOGIN_MODE=external` disables arbitrary-email development login and
  is required by final preflight; a real external identity provider remains a
  separate integration.
- A disposable PostgreSQL 16 acceptance run completed Alembic upgrade/downgrade
  and a two-user API flow with 2 users, 10 interests, 2 bookmarks, 2 events, and
  2 API keys.
- Reader Web moved from Next 14 to Next 16.3.5, PostCSS 8.5.28, and Playwright
  1.63.0. `npm ci`, zero-vulnerability `npm audit`, typecheck, production
  build, and 26 Playwright tests pass.
- Current backend evidence is 127 passed. Real OIDC/magic-link auth, production
  Paddle, real email, and production data remain outside this acceptance.

## Public Search And Upstream Boundary Acceptance

- A no-API-mock cross-process run used a disposable SQLite L1/L2 dataset, real L2
  HTTP on `127.0.0.1:18220`, and Public API on `127.0.0.1:18001` with
  `L3_USE_STUB_L2=false`.
- A query matching only the second of two articles returned that article with
  `next_cursor=null`, proving filtering occurred before pagination.
- Stopping L2 produced `l2_unavailable`, `retryable=true`, and `Retry-After: 2`;
  an invalid cursor produced `invalid_request` with HTTP 400.
- This acceptance used FakeLLM-derived persisted data and temporary SQLite. It did
  not contact production databases, paid models, real identity, email, or billing.
- A second run used disposable PostgreSQL 16 for L3 users, API keys, and quota
  usage while keeping real L2 HTTP and Public API processes. Two successful search
  calls returned content `2`, `next_cursor=null`, and persisted
  `api_usage_daily.count=2`.
- `scripts/run_public_api.py` now honors `PUBLIC_API_HOST`, `PUBLIC_API_PORT`, and
  `PUBLIC_API_RELOAD`; a regression test covers the runtime mapping.
