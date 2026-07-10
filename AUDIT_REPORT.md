# Phase 14.6 audit

## Replaced

- Place autocomplete, aliases, airport/metro selection and `/api/places/search` / `/api/places/resolve`.
- `originPlaceId` / `destinationPlaceId` and airport-ID compatibility.
- Candidate-hub cache and the unversioned browser search key.
- English-only homepage/results/verification UI and duplicate formatting helpers.
- Shared asyncio semaphore that failed across request event loops.

## Current alignment

- City catalog is backend-authoritative and bilingual.
- Search contract uses stable city IDs and a capped multi-airport matrix.
- Flight cache `v2` fingerprints all business dimensions and excludes locale.
- Frontend uses one i18n provider and one locale-aware formatting module.
- Structured selection works with keyboard buttons, Escape-to-close, backdrop close and responsive mobile layout.
- Protected and self-transfer semantics, price status, risk and verification remain backend-driven.

## Verification gates

The final command results for this working tree are recorded in the Phase 14.6 delivery response and release checklist.
