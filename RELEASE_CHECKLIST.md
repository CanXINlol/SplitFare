# SplitFare Release Checklist

Use this checklist before tagging or deploying the mock Release Candidate.

## Scope guardrails

- [ ] No live flight API is enabled by default.
- [ ] No Trip.com, Skyscanner, Duffel, airline, or OTA scraping is present.
- [ ] No browser-exposed supplier API keys exist.
- [ ] No payment, ticketing, login, or price-alert flow is enabled.
- [ ] Example/deep links are labelled as check-required or mock handoff links.
- [ ] Risk copy does not promise visa, baggage, delay, entry, or transfer feasibility.

## Automated checks

Run from the repository root unless noted.

- [ ] Backend tests pass:

  ```powershell
  cd backend
  .\.venv\Scripts\python.exe -m pytest -q
  ```

- [ ] Frontend type/lint gate passes:

  ```powershell
  cd frontend
  npm run lint
  ```

- [ ] Frontend unit tests pass:

  ```powershell
  cd frontend
  npm test -- --run
  ```

- [ ] Frontend production build passes:

  ```powershell
  cd frontend
  $env:NEXT_TELEMETRY_DISABLED="1"
  npm run build
  ```

- [ ] Playwright E2E passes:

  ```powershell
  cd frontend
  npm run test:e2e
  ```

## Manual smoke tests

- [ ] Search `Melbourne` to `Shanghai` and confirm ranked results appear.
- [ ] Search `墨尔本` to `上海` and confirm ranked results appear.
- [ ] Search `PVG` to `MEL` and confirm the empty state appears without a crash.
- [ ] Type an unsupported place and confirm a friendly validation error is shown.
- [ ] Confirm result cards display concrete airports such as `Melbourne (MEL)` and `Shanghai Pudong (PVG)`.
- [ ] Confirm split-ticket cards show self-transfer warnings.
- [ ] Confirm gap filters remove itineraries outside the selected range.
- [ ] Click `Check on Trip.com` and confirm the pre-booking verification modal opens.
- [ ] Confirm unavailable verification disables the continue CTA.
- [ ] Confirm price-change verification displays previous and current prices.

## Deployment readiness

- [ ] `README.md` reflects current setup, run, test, and mock limitations.
- [ ] `docs/DEPLOYMENT.md` has current Vercel and backend hosting instructions.
- [ ] `.env.example`, `frontend/.env.example`, and `backend/.env.example` are current.
- [ ] `GET /health` returns `status`, `version`, `mode`, and `timestamp`.
- [ ] Production `FRONTEND_ORIGIN` is explicit; wildcard CORS is not used.
- [ ] `NEXT_PUBLIC_API_BASE_URL` points to the deployed backend.
- [ ] `APP_ENV=production` does not expose raw stack traces or debug payloads.
- [ ] `ENABLE_MOCK_SUPPLIER` is intentionally set for the deployment mode.
- [ ] Search rate limiting is enabled with an appropriate `RATE_LIMIT_REQUESTS_PER_MINUTE`.
- [ ] Environment variables are documented and no secret is committed.
- [ ] Database migrations run successfully if Postgres persistence is enabled.
- [ ] Redis is optional; app works when cache is unavailable.
- [ ] Logs do not print supplier tokens, authorization headers, cards, passports, or payment data.
- [ ] Known limitations are visible to users and maintainers.

## Rollback plan

- [ ] Keep the previous working commit/tag available.
- [ ] Verify the app can run in mock-only mode with no external credentials.
- [ ] If live supplier work is introduced later, add a feature flag and keep mock fallback enabled.
