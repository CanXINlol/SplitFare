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
  → pure matching algorithm
  → risk engine + value ranking
  → booking options
  → POST /api/booking-options/verify
```

## Ownership boundaries

- `backend/app/cities.py` owns continents, countries, cities, airport mappings, priorities and matrix generation.
- Supplier adapters own raw response normalization and price verification capability.
- Matching and risk modules are pure business logic; they do not call React, databases or external APIs.
- Frontend dictionaries own user-facing zh/en copy. Backend sends stable error codes and business data.
- Backend owns all authoritative price, duration, savings, risk and ranking values.

## Location contract

Only city selection exists. Airport IDs, free text, aliases and `/api/places/*` do not exist. SearchRequest rejects unknown fields and requires `city:*` IDs. CityService rejects unknown or disabled cities and resolves up to three priority airports. The matrix caps hubs at 12 and supplier queries at the configured budget.

## Cache and state

- Supplier price TTL: mock 5 minutes, live policy 10 minutes.
- Cache namespace: `flight:v2`.
- Key dimensions: both city IDs, both resolved airport sets, route leg, date, passengers, cabin, min/max gap, currency and supplier mode.
- Locale is display-only and is excluded from flight cache keys.
- Browser state keys: `splitfare:locale:v1`, `splitfare:search:v2`; legacy key is deleted on form mount.
- Redis failure falls back to in-process memory or direct supplier fetch.

## Internationalization

`frontend/lib/i18n.tsx` contains the shared translation dictionary, persisted locale selection and stable warning mapping. `frontend/lib/format.ts` is the only money/date/time formatting layer. City names are bilingual catalog fields keyed by stable city ID. A locale change updates presentation only; the results fetch effect depends only on serialized search params.

## Safety

Production CORS is an explicit allowlist. Search has rate limiting and query/concurrency caps. Supplier errors are sanitized. Credentials in booking URLs are rejected and external HTTP URLs are rejected. Raw payload is filtered unless debug is explicitly allowed outside production. Mock prices are labeled as demo and no external link is presented as confirmed inventory.
