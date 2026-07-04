from datetime import date, datetime, timezone
from typing import Any

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapter
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceStatus,
    Supplier,
    SupplierCapabilities,
    VerificationStatus,
    VerifyPriceResult,
)


class SkyscannerSupplierAdapter(SupplierAdapter):
    @property
    def name(self) -> Supplier:
        return Supplier.skyscanner

    @property
    def display_name(self) -> str:
        return "Skyscanner"

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

    def _fetch_one_way(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> Any:
        raise AdapterNotConfiguredError("Skyscanner adapter skeleton has no API client configured.")

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if raw_response in (None, [], {}):
            return []
        raise AdapterNotConfiguredError("Skyscanner normalization mapping is not implemented.")

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        return VerifyPriceResult(
            offer_id=offer_id, supplier=self.name, status=VerificationStatus.unsupported,
            price_status=PriceStatus.redirect_only,
            supported=False,
            checked_at=datetime.now(timezone.utc),
            message="Skyscanner price verification is not configured.",
        )
