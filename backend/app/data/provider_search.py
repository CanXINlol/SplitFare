from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    display_name: str
    base_url: str
    supported_countries: tuple[str, ...]
    supported_locales: tuple[str, ...]
    supports_prefilled_route: bool
    supports_prefilled_date: bool
    enabled: bool = True
    route_template: str | None = None


# Public search entry points only. No prices are read and no affiliate tracking
# is attached. Precise route templates remain disabled unless a documented,
# contract-authorised format is configured.
PROVIDERS = (
    ProviderConfig("trip-com", "Trip.com", "https://www.trip.com/flights/", (), ("en", "zh"), False, False),
    ProviderConfig("skyscanner", "Skyscanner", "https://www.skyscanner.com/flights", (), ("en",), False, False),
    ProviderConfig("google-flights", "Google Flights", "https://www.google.com/travel/flights", (), ("en", "zh"), False, False),
    ProviderConfig("qantas", "Qantas", "https://www.qantas.com/au/en/book-a-trip/flights.html", ("AU",), ("en",), False, False),
)
