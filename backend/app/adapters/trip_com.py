from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlencode

from app.adapters.base import SupplierAdapter
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceStatus,
    Supplier,
    SupplierCapabilities,
    VerificationStatus,
    VerifyPriceResult,
)


TRIP_COM_TRACKING_ID = "SPLITFARE_PLACEHOLDER"


class TripComAffiliateAdapter(SupplierAdapter):
    @property
    def name(self) -> Supplier:
        return Supplier.trip_com_affiliate

    @property
    def display_name(self) -> str:
        return "Trip.com"

    @property
    def capabilities(self) -> SupplierCapabilities:
        return SupplierCapabilities(
            supports_search=False,
            supports_price_verify=False,
            supports_booking_url=True,
            supports_baggage_info=False,
            supports_split_ticket=False,
            supports_live_price=False,
            supports_affiliate_link=True,
        )

    def build_deep_link(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> str:
        query = urlencode({
            "origin": origin, "destination": destination,
            "date": departure_date.isoformat(), "passengers": passengers,
            "cabin": cabin.value, "currency": currency,
            "tracking_id": TRIP_COM_TRACKING_ID,
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

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        return VerifyPriceResult(
            offer_id=offer_id, supplier=self.name, status=VerificationStatus.unsupported,
            price_status=PriceStatus.redirect_only,
            supported=False,
            checked_at=datetime.now(timezone.utc),
            message="Affiliate deep links do not provide price verification.",
        )
