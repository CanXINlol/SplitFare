from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlencode

from app.adapters.base import SupplierAdapter
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceVerification,
    Supplier,
    VerificationStatus,
)


class TripComAffiliateAdapter(SupplierAdapter):
    @property
    def name(self) -> Supplier:
        return Supplier.trip_com_affiliate

    def build_deep_link(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> str:
        query = urlencode({
            "origin": origin, "destination": destination,
            "date": departure_date.isoformat(), "passengers": passengers,
            "cabin": cabin.value, "currency": currency,
            "tracking": "SPLITFARE_PLACEHOLDER",
        })
        return f"https://example.invalid/tripcom-affiliate?{query}"

    def _fetch_one_way(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> Any:
        return {
            "deep_link": self.build_deep_link(
                origin, destination, departure_date, passengers, cabin, currency
            )
        }

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        # Affiliate skeleton intentionally has no fare payload to normalize.
        return []

    def verify_price(self, offer_id: str) -> PriceVerification:
        return PriceVerification(
            offer_id=offer_id, supplier=self.name, status=VerificationStatus.unavailable,
            checked_at=datetime.now(timezone.utc),
            message="Affiliate deep links do not provide price verification.",
        )
