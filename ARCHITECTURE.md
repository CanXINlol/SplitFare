# SplitFare Architecture

## Request path

```text
Next.js I18nProvider + CityCatalogProvider
  → GET /api/cities
  → structured continent/country/city selector
  → POST /api/search (originCityId, destinationCityId)
FastAPI CityService
  → ResolvedCity airport sets
  → capped AirportSearchMatrix
  → parallel SupplierOrchestrator
  → Duffel API v2 (only in explicit sandbox/live mode)
  → pure matching algorithm
  → risk engine + value ranking
  → booking options
  → POST /api/booking-options/verify
  → POST /api/booking-options/redirect-confirmed (only for a server-authorised URL)
```

## Ownership boundaries

- `backend/app/cities.py` owns continents, countries, cities, airport mappings, priorities and matrix generation.
- Supplier adapters own raw response normalization and price verification capability.
- `DuffelSupplierAdapter` receives only concrete IATA airport codes, uses a server-only token, and never receives city display names.
- Matching and risk modules are pure business logic; they do not call React, databases or external APIs.
- Frontend dictionaries own user-facing zh/en copy. Backend sends stable error codes and business data.
- Backend owns all authoritative price, duration, savings, risk and ranking values.

## Location contract

Only city selection exists. Airport IDs, free text, aliases and `/api/places/*` do not exist. SearchRequest rejects unknown fields and requires `city:*` IDs. CityService rejects unknown or disabled cities and resolves up to three priority airports. The matrix caps hubs at 12 and supplier queries at the configured budget.

## Cache and state

- Supplier price TTL: mock 5 minutes; Duffel TTL is configurable and disabled unless the supplier cache policy is explicitly allowed.
- Cache namespace: `flight:v3`.
- Key dimensions: both city IDs, both resolved airport sets, route leg, date, passengers, cabin, min/max gap, currency and supplier mode.
- Locale is display-only and is excluded from flight cache keys.
- Browser state keys: `splitfare:locale:v1`, `splitfare:search:v2`; legacy key is deleted on form mount.
- Redis failure falls back to in-process memory or direct supplier fetch.

## Internationalization

`frontend/lib/i18n.tsx` contains the shared translation dictionary, persisted locale selection and stable warning mapping. `frontend/lib/format.ts` is the only money/date/time formatting layer. City names are bilingual catalog fields keyed by stable city ID. A locale change updates presentation only; the results fetch effect depends only on serialized search params.

## Safety

Production CORS is an explicit allowlist. Search has rate limiting and query/concurrency caps. Supplier errors are sanitized. Credentials, unsafe protocols, example hosts, unlisted supplier domains and external HTTP booking URLs are rejected. The client submits no price or URL during verification/redirect confirmation. Raw payload is filtered unless debug is explicitly allowed outside production. Mock prices are labeled as demo and no external link is presented as confirmed inventory.

## Verification and redirect ownership

Supplier adapters return `VerifyPriceResult`; the API maps that internal result to the user-facing pre-booking state machine. Canonical BookingOptions are stored server-side by search/itinerary/option ID. Analytics payloads contain IDs, supplier and status only. Redirect-only options never enter confirmed-price ranking, and the active Phase 16 supplier has no booking URL capability.

## Supplier mode isolation

- Mock: only deterministic mock search adapters.
- Sandbox: only Duffel test-mode search; response must contain `live_mode=false`.
- Live: only Duffel live search; response must contain `live_mode=true`.
- Sandbox/live authentication, timeout, rate limit, invalid response and unavailable conditions use stable uppercase error codes.
- All real supplier failures produce `SearchStatus.failed`; they never silently insert mock fares.
