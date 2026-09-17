# Reader Web product and UX refactor

Status: implementation baseline for the September 2026 local acceptance round.

## Product position

CodePick Reader is a bilingual engineering reading workspace for developers who need a small, traceable queue of useful public-source material. The first screen must answer three questions: what is relevant today, where did it come from, and why did the system place it in the queue.

The primary loop is:

1. scan a short feed;
2. verify the source and processing provenance;
3. open the source or inspect the automated analysis;
4. save an item locally or to an authenticated account;
5. return to the saved library.

Revenue, retention, personalization quality, and willingness to pay remain hypotheses. The UI must not imply that test scores, fixture translations, local sessions, sandbox checkout, or empty usage charts are production evidence.

## Audit findings

- The navigation gives experimental distribution and billing pages the same weight as reading and saving.
- The feed repeats its heading, emphasizes precise L2 scores, and does not explain whether an item came from a public source, fixture, heuristic, simulated scorer, or reviewed editor.
- The detail page visually mixes publisher material, translated material, and generated analysis.
- `ReadingActions` reports local success after a failed API request without persisting the action.
- `SaveLaterButton` stores only ids and has no library route, so readers cannot reliably revisit saved material.
- Companion, recommendations, brief, login, pricing, and API controls can look production-ready while they are local or sandbox workflows.
- `/` returns 404 and unsupported locale segments render the English shell instead of a real not-found response.
- Empty, upstream-error, and not-found states need separate guidance.

## Implementation decisions

- Make Reader and Saved the primary navigation. Keep Brief visible but describe its current public/test boundary. Put developer and pricing workflows in a secondary menu.
- Add search to the feed and preserve real Reader API/L2 fetching. Demo fallback remains opt-in for the existing isolated browser suite.
- Add provenance fields to the front-end contract and render plain-language badges: public source or fixture, rule/simulated/model analysis, and reviewed/unreviewed.
- Treat exact scores as processing detail rather than objective quality. The list shows a provenance summary; the detail page can expose score dimensions with a clear method label.
- Store a traceable local saved snapshot (id, title, source, URL, summary, date, provenance), expose it at `/{locale}/library`, and keep account bookmark errors honest.
- Present the source excerpt before automated analysis. Only expose translation controls when translation data is actually available, and label fixture/simulated translations.
- Mark local identity, companion fallback, sandbox billing, and local API keys as development workflows.
- Redirect `/` to `/zh`. Reject unsupported locales with a 404.
- Preserve keyboard focus, semantic headings, status announcements, 44px touch targets, reduced motion, and single-column mobile reading.

## Acceptance

- `npm run typecheck`
- `NEXT_TELEMETRY_DISABLED=1 npm run build`
- the existing Playwright suite plus root redirect, unknown-locale 404, provenance, local save/revisit/remove, and mobile navigation coverage
- M2 real-data browser checks must continue to run with demo fallback disabled and no API mocks

### 2026-09-17 local result

- TypeScript and the independent Next.js 16.3.5 production build passed.
- The isolated fixture suite passed 40/40 checks: 20 scenarios in desktop Chromium and Pixel 5.
- The public-source preview passed a no-mock browser check against port 13200. It covered provenance, an HTTPS publisher link, local save persistence, the saved library, heuristic presentation, and the explicit no-translation state.
- Browser-side Reader API calls now default to same-origin `/api` routes; an explicit `NEXT_PUBLIC_READER_API_BASE` remains available for intentional cross-origin setups. Server rendering continues to use `READER_API_BASE`.
- Development sign-in no longer invents a token when Reader API is unavailable. A confirmed session survives bookmark-sync failure, local saves are retained until every sync succeeds, and corrupt local save data cannot overwrite the real account identity. The remote-friendly login timeout is 10 seconds.
- A second no-mock check against port 13200 created an isolated development identity, verified it through `/api/me`, persisted content 6 as an account bookmark across reload, and confirmed companion usage incremented its stored quota from 0 to 1.
- A failed server-side API-key revocation keeps the real key active and reports a retryable failure. Only explicit `cp_demo_` keys use the local demo lifecycle. Admin writes likewise expose explicit API failure and use a bounded request timeout.
- The retained M1 preview passed a separate no-mock browser check against port 13210. It confirmed that stored FakeLLM scores and the Chinese translation remain visible and are labeled as simulated output.
- The 390px Chinese layout has no document-level horizontal overflow. Header items keep a normal 41–44px height and remain on one line inside an explicitly scrollable navigation row.
- The route error boundary uses the Next.js 16 retry() contract, which re-fetches the failed Server Component instead of only clearing the error state.
- Screenshots were generated during acceptance at /tmp/codepick-reader-desktop.png and /tmp/codepick-reader-mobile.png; they are machine-local evidence and are not committed.

These checks validate local product behavior, not real model quality, production identity, payment, email, or content redistribution rights.
