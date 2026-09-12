# L3 Sprint Handoff

This file captures the sprint-level delivery notes required by the L3 plan. The workspace is not currently a Git repository, so these notes serve as the durable commit-equivalent handoff record for implemented features, self-test evidence, coverage, and remaining work.

## Current Verification

- Full handoff gate: `python scripts/l3_verify.py` -> `L3 VERIFY: PASS`
- Backend contracts: `108 passed`
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
- Coverage/evidence: included in `108 passed` backend contracts and `26 passed` Playwright E2E.
- Remaining work: final integration must validate `/v1` and MCP against production API key storage and real L2 content.

## Final Integration Residuals

- Real PostgreSQL `DATABASE_URL` with SQLAlchemy repository and quota backends.
- Real HTTPS L2 provider endpoint and optional `L2_API_KEY`.
- Redis/Arq worker runtime using explicit `ARQ_REDIS_HOST` and `ARQ_REDIS_PORT`.
- Resend or SES credentials and sender identity.
- Paddle production checkout URL and signed webhook delivery.
- Go/no-go execution using `docs/L3-final-integration-checklist.md`.
