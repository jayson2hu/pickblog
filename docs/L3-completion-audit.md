# L3 Completion Audit

This audit maps the requested L3 scope to current evidence. It separates the independent-development deliverable from final integration, because the L3 contract requires stub L2 and sandbox/mock providers during development, with real L2/payment/email/worker services switched on only during final integration.

## Verdict

- Independent L3 application and distribution layer: current local gates are green, including the full `l3_verify.py` wrapper.
- Final integration with real L2, PostgreSQL, Redis/Arq, Resend/SES, and Paddle: prepared and gated, not executed in this local environment because those external services and secrets are intentionally absent.

## Requirement Evidence

| Requirement | Evidence |
|---|---|
| E0 engineering baseline: Next.js App Router, Reader API, Public API, migration | `apps/reader-web`, `services/reader-api`, `services/public-api`, `db/alembic/versions/0001_l3_owned_tables.py`; `l3_verify.py` runs preflight, migration smoke, backend smoke, typecheck, build, E2E, cleanup. |
| E1 content input through `ContentReadProvider` with stub and real-L2 switch | `services/shared/codepick_l3/provider.py` defines `ContentReadProvider`, `StubContentReadProvider`, `L2HttpContentReadProvider`, and `L3_USE_STUB_L2=false` switch; tests cover stub fixtures and HTTP provider paths. |
| E2 public picks, detail, bilingual display, pagination, SEO baseline | Reader routes under `apps/reader-web/app/[locale]`; `apps/reader-web/tests/reader.spec.ts` covers public picks, detail analysis, translation behavior, sitemap, and SEO JSON-LD. |
| E3 account/JWT and centralized Pro gate | `services/shared/codepick_l3/auth.py` implements `current_user` and `require_plan`; tests cover 401, forged plan rejection, subscription-backed plan state, and absence of scattered `user.plan ==` route checks. |
| E4 interests, follows, bookmarks, recommendations, behavior events, north-star metric | Reader API routers plus `repository.py`; tests cover interest validation, follows, bookmarks, recommendations, click/deep_read/bookmark/not_interested events, non-completed rejection, and `deep_read_closed_loop_rate`. |
| E5 AI companion with Free quota and Pro bypass | `reader_api/routers/companion.py`, `companion_usage`; tests cover SSE contract, quota exceeded 429, Pro bypass, and non-completed rejection before usage mutation. |
| E6 public/personal brief generation, worker, email | `briefs.py`, `workers/briefs/jobs.py`, `email.py`; tests cover public/personal generation, deduplication, completed-only items, Arq worker config, mock email, Resend payload, SES payload, and transport failure mapping. |
| E7 USD commercial flow and signed webhook | `billing.py`, `reader_api/routers/billing.py`; tests cover month/year/earlybird checkout, USD query, Paddle runtime switch, activation, transaction completion, cancellation, missing user, unknown event, and bad signature rejection. |
| E8 Public API and MCP | `services/public-api/public_api/routers/v1.py`, `services/mcp-server/server.py`, `public_contract.py`; tests cover API key auth, read scope, RPM, daily quota, quota envelope, pagination, exact public fields, completed-only filtering, taxonomy endpoints, and MCP parity. |
| E9 i18n and SEO | `apps/reader-web/app/[locale]`, sitemap and metadata code; Playwright covers English/Chinese routes, localized account controls, sitemap, detail metadata, and JSON-LD. UTF-8 guard tests cover Chinese copy and fixture translations. |
| `/api` and `/v1` trust boundary separation | `reader_api/main.py` mounts `/api` routers with JWT dependencies; `public_api/main.py` mounts `/v1` with API key dependencies. Tests assert `/v1` does not import internal reader auth/repository state and `/api` protected routes reject missing JWT. |
| Public field filtering and privacy boundary | `public_contract.py` is shared by `/v1` and MCP; tests assert no `base_analysis` or `translations` in public responses and reject non-`COMPLETED` content. |
| L3-owned tables only | `models.py` and Alembic migration define only `users`, `subscriptions`, `user_interests`, `user_follows`, `reading_events`, `briefs`, `bookmarks`, `api_keys`, `api_usage_daily`, `companion_usage`; migration smoke verifies upgrade/downgrade. |
| Independent development defaults | `.env.example`, `readiness.py`, and `l3_preflight.py` default to stub L2, memory repository/quota, sandbox billing, mock email, and local Redis defaults; tests verify dev readiness. |
| Final integration reservation | `l3_preflight.py --final` checks final config shape; `l3_final_probe.py` performs live L2/PostgreSQL/Redis/email/Paddle probes in a target environment and is non-destructive unless explicit side-effect flags are used. |
| CI and local verification | `.github/workflows/l3-ci.yml` runs backend preflight/migration/smoke/cleanup and reader-web npm ci/typecheck/build/Playwright E2E; `make l3-verify` delegates to the full local verifier. |
| Sprint handoff requirement | `docs/L3-sprint-handoff.md` records S1-S5 implemented features, self-test evidence, coverage, and final-integration residuals. The workspace is not a Git repository, so this is the durable commit-equivalent handoff record. |

## Latest Verified Gates

- Rechecked on 2026-06-08 after L3 redesign work.
- `python scripts/l3_preflight.py` -> dev mode `status=ready`.
- `python scripts/l3_migration_smoke.py` -> `L3 MIGRATION: PASS`; created tables now include `taxonomy_categories`, `audiences`, and `audience_categories`.
- `python scripts/l3_smoke.py` -> `108 passed`; `L3 PIPELINE: PASS`.
- Reader Web typecheck: `npm --prefix apps/reader-web run typecheck` -> passed.
- Reader Web production build: `npm --prefix apps/reader-web run build` -> passed after cleaning stale `.next`.
- Reader Web Playwright: `npm --prefix apps/reader-web run test:e2e` -> `26 passed`.
- `python scripts/l3_verify.py` -> `L3 VERIFY: PASS`; includes preflight, migration smoke, backend smoke, typecheck, production build, cleanup, and all 26 Playwright tests.
- Cleanup note: `.pytest_cache` is locked on this Windows workspace and is reported as skipped by `l3_clean.py`; generated L3 artifacts are removed successfully.
- Final preflight: `python scripts/l3_preflight.py --final` remains expected to block until real L2, PostgreSQL, Redis/Arq, email, Paddle, and production secrets are configured.

## L3 Redesign Evidence

- M1/M2 frontend shell and reading core: redesigned `Header`, theme toggle, account menu, feed filters, cover thumbnails, read-time/reason cards, save-later, adaptive sidebar, detail cover/original link, bilingual body, score explainer, and conversational companion.
- M3/M4 foundation APIs: added `GET /api/me`, `PATCH /api/me/audience`, `GET /api/taxonomy`, `GET /api/companion/quota`, admin taxonomy CRUD, and public `GET /v1/taxonomy` with public field filtering.
- Epic E persistent taxonomy: added Alembic `0002_taxonomy.py`, ORM models for `taxonomy_categories`, `audiences`, and `audience_categories`, memory/SQLAlchemy repository CRUD, admin permission checks, audience-category assignment, and user audience selection.
- M5 surface split: moved API key management to `/[locale]/developers`, moved billing to `/[locale]/pricing`, kept login focused on session and interests, and connected `/[locale]/admin` to taxonomy management.
- M6 redesign fixes: connected feed `vertical/sort/cursor` query handling, taxonomy-backed chips, load-more pagination, companion quota headers and UI, admin CRUD gate/edit/delete/category assignment, `/api/me` session hydration, interest/sidebar sync, saved-item login sync, dismissible signed-in hero, and 7-day API usage reporting.

## Open Completion Items

- Execute final integration only in the target environment after supplying real L2, PostgreSQL, Redis/Arq, Resend/SES, Paddle, and non-default production secrets.

## Final Integration Gate

Before production cutover, run:

```bash
python scripts/l3_preflight.py --final
python scripts/l3_final_probe.py
python scripts/l3_final_probe.py --send-test-email ops@example.com --enqueue-brief
```

The local development environment is expected to block `l3_final_probe.py` at final preflight until real external service configuration is supplied.
