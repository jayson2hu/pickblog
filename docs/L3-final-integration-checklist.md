# CodePick L3 Final Integration Checklist

Use this checklist when switching L3 from independent development to final integration with real L2, PostgreSQL, Redis/Arq, email, and Paddle.

## Scope

- Reader Web, Reader API `/api`, Public API `/v1`, MCP wrappers, daily brief workers, billing webhooks, and L3-owned persistence.
- L3 remains read-only for L0-L2 content, score, and translation data through `ContentReadProvider`.
- Public `/v1` remains API-key scoped and must not expose recommendation decisions or private user context.

## Required Evidence

- `python scripts/l3_verify.py` prints `L3 VERIFY: PASS`.
- `python scripts/l3_preflight.py --final` prints `status=ready` with non-default secrets and real integration switches.
- `python scripts/l3_final_probe.py` prints `status=ready` in the target environment for live L2, PostgreSQL, Redis/Arq, email provider config, and Paddle config checks.
- `python scripts/l3_final_probe.py --send-test-email ops@example.com --enqueue-brief` passes during release rehearsal after operators approve the real email and queue side effects.
- `python scripts/l3_migration_smoke.py` passes against a disposable database; repeat with `L3_MIGRATION_SMOKE_DATABASE_URL` pointed at the PostgreSQL integration database before launch.
- Reader Web `npm run build` and `npm run test:e2e` pass in CI.
- Backend pytest includes webhook signature, quota/rate limit, `require_plan`, MCP/public field filtering, and migration coverage.

## Final Switches

- `L3_USE_STUB_L2=false`
- `L2_BASE_URL` is an HTTPS L2_BASE_URL and points to the real L2 read API; `L2_API_KEY` is configured if required.
- `L3_REPOSITORY_BACKEND=sqlalchemy`
- `L3_QUOTA_BACKEND=sqlalchemy`
- `DATABASE_URL` uses a PostgreSQL URL (`postgresql://` or `postgresql+driver://`) and points to the L3 PostgreSQL database.
- `ARQ_REDIS_HOST` and `ARQ_REDIS_PORT` are explicitly set and point to the Redis/Arq runtime.
- `EMAIL_PROVIDER=resend` with `RESEND_API_KEY` and `EMAIL_FROM`, or `EMAIL_PROVIDER=ses` with `SES_REGION` and `EMAIL_FROM`.
- `BILLING_ENVIRONMENT=production`
- `PADDLE_CHECKOUT_BASE_URL` is an HTTPS production Paddle checkout URL, not sandbox.
- `PADDLE_WEBHOOK_SECRET` and `JWT_SECRET` are non-default secrets.
- Pricing remains USD: `$8/month`, `$79/year`, `$4.9` early bird.

## Go/No-Go

- Go only if all required evidence above is attached to the release record.
- No-go if `/api` accepts API keys, `/v1` accepts JWT-only auth, `require_plan` is bypassed, public fields include private context, or final preflight is blocked.
- No-go if `l3_final_probe.py` cannot reach real L2, PostgreSQL, Redis/Arq, or configured email/Paddle services.
- No-go if Redis/Arq cannot enqueue a public brief job or email delivery cannot send a mock/test brief through the configured provider.
- No-go if Paddle signed webhook activation and cancellation cannot promote and downgrade a test user.

## Rollback

- Revert traffic to the previous L3 deployment.
- Keep the database schema at the last successfully migrated revision unless rollback requires an explicit Alembic downgrade approved by the release owner.
- Set `BILLING_ENVIRONMENT=sandbox`, `EMAIL_PROVIDER=mock`, and `L3_USE_STUB_L2=true` only in non-production recovery environments.
- Disable public API keys at the edge if `/v1` quota or field filtering regresses.

## Post-Release Checks

- Verify `/api/ready` and `/v1/ready` report the expected production switches.
- Verify Reader Web can render public picks, localized detail pages, daily brief, login, Pro brief, companion, billing checkout, and API key lifecycle.
- Verify daily brief worker schedule and one manual enqueue.
- Verify north-star metric contains `deep_read_closed_loop_rate` and does not optimize DAU or reading time.
