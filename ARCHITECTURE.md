# SplitFare Architecture — Route Discovery

## Active request path

```text
Next.js structured city selector
  → POST /api/routes/discover
FastAPI CityService
  → airport sets
RouteDiscovery
  → regional HubConfig
  → AirportGeo great-circle distances
  → detour filtering + route signature dedupe
  → structural risk + schedule-unknown warnings
  → route ranking
  → ProviderSearchLink factory
Next.js RouteCard
  → provider search reminder
  → local ManualComparison workspace
  → integer minor-unit calculations
  → versioned localStorage
```

## Ownership

- `cities.py`: city hierarchy and city-to-airport mapping.
- `data/route_hubs.py`: regional Hub policy and connectivity metadata.
- `data/airport_geo.py`: sole airport coordinate source.
- `route_discovery.py`: pure distance, detour, dedupe, risk, ranking and provider-link orchestration.
- `data/provider_search.py`: central platform entry configuration; never React.
- `manual-pricing.ts`: validation, minor-unit arithmetic, comparison rules and local persistence.
- Frontend: presentation and locale formatting only; it never computes authoritative route risk.

## Safety boundaries

- Route discovery performs no supplier HTTP calls.
- Candidate routes contain no flight number, exact departure/arrival time or system price.
- Provider URLs are backend-generated HTTPS URLs; unsupported prefill falls back to a homepage/manual search.
- Redirect-only links never become confirmed prices or enter ranking.
- Manual values are explicitly user-entered and remain in the browser.
- Locale is excluded from route discovery state; switching language does not repeat discovery.

## Legacy boundary

The price-era `/api/search` and adapter contracts remain isolated for regression and future authorised integrations. The active product UI uses only `/api/routes/discover` and cannot surface legacy Mock prices.
