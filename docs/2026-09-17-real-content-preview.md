# Real-content reader refactor

Status: reader implementation and browser acceptance passed, 2026-09-17; Alembic/SQLite account-write correction has also passed backend acceptance. Historical tests are not evidence of this change passing.

The reader serves developers deciding what to read and save. API root URLs should guide visitors to documentation. Feed search must be forwarded before L2 pagination. Content provenance, original language, reading estimates and translation availability must survive L2-to-reader mapping. The reader never computes L2 scores or writes L0/L1/L2 data.

The user interface is redesigned around discover → understand source → read original → save/revisit. Empty, upstream-error and unavailable-translation states must be honest. Real-source preview uses isolated SQLite, development authentication and no paid models, mail or payments. Guest bookmarks must clearly state their local scope.

## Executed acceptance

- Backend final: **166 passed**, smoke/development preflight/isolated SQLite and real PostgreSQL 16 migration round-trip PASS. A real development-login probe exposed SQLite migration BIGINT primary keys, which schema-only migration smoke had not caught. Forward migration `0003_sqlite_generated_ids` corrects six generated-ID tables only on SQLite. Ten new checks prove real login/follow/event/bookmark/API key/quota/subscription/brief inserts, preservation of 64-bit IDs/all rows/foreign keys/indexes across upgrade/downgrade, FK setting restoration and full rollback on failure. PostgreSQL is unchanged. The local preview was backed up and upgraded through Alembic; development login and extractive companion succeeded with persisted quota 0→1.
- TypeScript and independent Next.js 16.3.5 production build PASS; npm audit: zero vulnerabilities.
- 40 fixture browser checks passed (20 scenarios × desktop/Pixel 5). Two no-API-mock cases passed separately: public-source reading/save/revisit, and a unique development account proving same-origin login, /me, SQL bookmark persistence after refresh, extractive companion and quota 0→1; M1 FakeLLM score/translation compatibility passed against an independent current-schema fixture environment.
- Actual L2 pause showed an honest error with no fixture replacement. After API recovery, the same page's Next 16 `retry()` button reloaded real content. The independent recovery script passed without browser page errors.
- Desktop and 390px screenshots were inspected. A first screenshot exposed vertically wrapped mobile navigation; the corrected navigation keeps 44px one-line controls within its own horizontal scroll row and does not overflow the document.

## Remote browser routing

All browser components default to the same-origin `/api` proxy through `clientApiUrl()`. An internal server address such as `127.0.0.1:8000` must not become a request to a remote visitor's computer. Server-side reads keep their explicit internal provider target. Only forwarding the web port is sufficient for normal reading/account operations.

Login errors no longer fabricate demo JWTs, plans or administrator access inferred from email prefixes. Bookmark-sync failure retains the real session and local saves, with a distinct warning. Invalid local save data is not treated as successful synchronization. Failed server-side API key revocation keeps the real key active; administration writes report failures instead of claiming success; only explicitly labeled `cp_demo_` keys support a local demonstration lifecycle.

## Backend safety fixes

Feed q is forwarded to L2 before pagination. Missing publication dates remain null. Language, reading estimates, tags and provenance survive the reader contract; public API provenance is an explicit safe-field whitelist. API roots redirect to docs. Unknown IDs, malformed requests, configuration failures and temporary upstream failures remain separate.

Companion's finite upstream chunks are materialized before sending SSE headers. Upstream failure or content removal does not produce HTTP 200 or charge a successful request. The quota endpoint now reads the active repository, including persistent SQL, not an unrelated global memory counter. Multiline excerpts retain each SSE data prefix. Tests cover memory and SQLite, initial/partial upstream failure, 404/400/configuration/transient classifications, successful counts, exhausted quota and empty output. This is not a claim of distributed atomic quota reservations or future live-model streaming.

Source databases and captured article bodies are outside Git. Real-source preview uses `extractive-v3` plus `heuristic-v1`, no translation or paid LLM. Authentication is still development email login, not verified identity. Payments are sandbox and mail mock.

See [Reader UX](../apps/reader-web/UX_REDESIGN.md), [private preview / remote access](../../codepick-docs/REAL_CONTENT_PREVIEW.md), and [platform acceptance](../../codepick-docs/PRODUCT_ACCEPTANCE_2026-09-17.md).
