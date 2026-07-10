# Phase 14.5 Audit Report

Date: 2026-07-10  
Verdict: **ALIGNED after repair**  
Production readiness: **NOT READY — final release gates blocked by local execution environment**

## Executive summary

The repository contained a functioning mock happy path, but several Phase 11.5–14 concepts were not connected safely in the real flow. The most serious findings were production-default mock enablement, redirect-only adapters being queried as flight suppliers, no total supplier-query cap, mock falsely advertising live-price capability, duplicated price-state enums, and a verification API that trusted client-supplied price and redirect URL.

The implementation was repaired in place. Location → matrix → supplier → normalization → matching → risk → response → booking → verification now uses explicit contracts and server-side binding. Backend tests and both frontend static gates pass. Final Vitest/Playwright/build/Docker gates could not all be rerun because the execution environment exhausted approval credits and Docker Desktop was not running; therefore this report does not claim release readiness.

## Initial failures and misleading passes

- Baseline frontend typecheck, one Vitest test, Next build, 164 backend tests and four E2E tests passed.
- The baseline `npm run lint` was only `tsc --noEmit`; no ESLint ran.
- Ruff was configured but not installed.
- Frontend unit coverage was one card-render test.
- E2E had four mobile happy/validation paths and treated reverse-airport empty state as the only exact-airport test.
- Docker Desktop daemon was not running, so Docker gates were unavailable.
- `npm ci`, Vitest, build and Playwright require out-of-sandbox child processes on this Windows host.

## Product drift found

1. Backend Docker production image defaulted to mock enabled.
2. Mock supplier declared `supports_live_price=true`.
3. Trip.com redirect adapter was present in the search adapter list and queried despite `supports_search=false`.
4. Airport matrix had airport/hub caps but no total supplier-query cap or truncation metadata.
5. Same-day second-leg queries did not operationally cover overnight layovers.
6. Mock timestamps used UTC for all airports and based price freshness on departure date rather than check time.
7. Split itinerary total price was attached to a single first-offer booking option and verified as if one supplier sold the whole itinerary.
8. Verification accepted previous price and arbitrary booking URL from the browser, allowing option misbinding/open redirect.
9. `PriceConfidence` duplicated and could conflict with `PriceStatus`.
10. Frontend autocomplete lacked keyboard navigation and complete ARIA combobox semantics.
11. Results did not expose searched airport sets or matrix truncation.
12. Production docs described placeholder/example links and an obsolete frontend env variable.

## Repairs

### Architecture

- Capability routing now excludes non-search adapters.
- Supplier calls have a semaphore, per-leg offer cap, total timeout and total supplier-query cap.
- `build_search_queries` is pure, deterministic, date-aware and returns truncation details.
- Second legs query the required operational dates for overnight gaps without exposing multi-date user search.
- Matcher indexes second legs by connectable origin airport instead of blind all-offer nested matching.
- SearchResponse metadata now carries searched/excluded airports, supplier errors, query counts, freshness counts and mock/live mode.
- Amount fields use backend `Decimal` and serialize to numeric JSON.

### Security and production isolation

- Production mock default is false in settings and Docker image.
- Production demo requires explicit mock enablement and surfaces Demo Data.
- Mock mode disables live Duffel search even if a token exists, preventing mixed ranking.
- Production wildcard CORS is rejected.
- Location query length is limited; search input and matrix limits are enforced.
- Booking URLs reject dangerous protocols, embedded credentials and non-local plain HTTP.
- Verification accepts only search, itinerary and booking-option IDs and resolves the canonical server record.
- Production debug/raw payload and raw exception tests were added.
- Error messages continue to redact token, API key, Authorization and Bearer values.

### Price and booking correctness

- `PriceStatus` is the single price-state enum.
- Cache-hit offers are marked cached; expired confirmed options downgrade to cached.
- Redirect-only options have no amount and never create flight offers.
- Split itineraries expose one supplier option per ticket; option prices sum to itinerary total.
- Mock offer IDs include date, passenger count, cabin and currency so later verification is stable.
- Mock verification now covers unchanged, changed and unavailable states.

### UX and accessibility

- Autocomplete has debounce, loading, empty, error, ArrowUp/ArrowDown/Enter/Escape, listbox roles and active descendant.
- Search submit is duplicate-protected and session state is restored when returning.
- Loading explains airport/hub comparison.
- Result header shows actual airport sets, hubs, Demo Data and truncation.
- Partial supplier errors are non-blocking and visible.
- Duplicate decision groups merge rather than repeat the same itinerary as separate recommendations.
- Negative savings no longer render as “Save -$…”.
- Booking modal uses canonical options, Escape close, focus placement and accessible title/description binding.

## Tests added or updated

- Real Chinese aliases, MEL autocomplete, city/airport resolution and capped matrix metadata.
- Timezone-aware gap, DST boundary and next-day supplier queries.
- Search-capability routing, mock timeout/partial, standardized failures and cache price status.
- Decimal model behavior, legacy SearchRequest rejection and OpenAPI contract fields.
- Production mock default, explicit demo, wildcard CORS, raw payload safety and unsafe URL rejection.
- Canonical verification unchanged/changed/unavailable, redirect unsupported and itinerary misbinding.
- Frontend autocomplete keyboard/error tests and canonical verification request test.
- Playwright suite expanded from 4 to 10 scenarios: English/Chinese city, exact airport, invalid, empty, partial, protected/split, unchanged/changed/unavailable, redirect-only and 375px viewport (some requirements share one test).

## Verified results

- Backend Ruff: passed.
- Backend pytest: **183 passed**; two warnings are from an old `.pytest_cache` ACL that the environment would not permit deleting.
- Frontend typecheck: passed.
- Frontend ESLint with zero-warning policy: passed.
- Frontend Vitest before the final PriceStatus consolidation: **5 passed**.
- Playwright intermediate run: **3 passed, 1 failed** only because the expected accessible dialog name changed; the selector was repaired and the suite was then expanded, but final execution was blocked by approval limits.
- Baseline frontend production build before Phase 14.5 repair: passed; final build not rerun.
- Docker: client installed, daemon unavailable.
- Docker Compose configuration: `docker compose config --quiet` passed.

## Remaining limitations / technical debt

- Booking registry and rate limiter are in-process. Multi-instance production requires shared short-TTL storage; until then deploy only a single-instance demo.
- Seed place coverage remains finite and is not a geocoder.
- Historical CitySeed alias literals include legacy code-page artifacts, but runtime exposes only the canonical Unicode override catalog. Removing those dead literals is a Phase 14.6 cleanup candidate.
- Supplier verification is synchronous; a real adapter needs an async timeout-aware verify implementation.
- No real supplier, booking, payment, FX, visa or ground-transport service is validated.
- Database health is degraded safely but not reported as a dependency status in `/health`.

## Blocking issues

1. Final Vitest, Playwright and Next production build require child-process approval; the environment rejected further escalations after its usage limit.
2. Docker Desktop daemon is not running, so backend/image/Compose smoke gates are not verified.
3. Old `backend/.pytest_cache` has a Windows ACL issue; deletion approval was rejected by the same environment limit.
4. The in-app browser policy rejected access to `http://127.0.0.1:8081`, so no additional visual smoke run could supplement Playwright.

These are release-gate blockers, not reasons to fake completion. Resume the gate after the approval window resets and Docker Desktop is available.

## Production readiness

**NOT READY**

The product implementation is aligned, but Phase 14.5 cannot be declared complete until the unchecked automated gates in `RELEASE_CHECKLIST.md` pass. The next work item may only be Phase 14.6 release-gate closure and shared-state hardening; Phase 15 should not start yet.
