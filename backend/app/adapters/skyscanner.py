from datetime import date, datetime, timezone
from typing import Any

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapter
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceVerification,
    Supplier,
    VerificationStatus,
)


class SkyscannerSupplierAdapter(SupplierAdapter):
    @property
    def name(self) -> Supplier:
        return Supplier.skyscanner

    def _fetch_one_way(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> Any:
        raise AdapterNotConfiguredError("Skyscanner adapter skeleton has no API client configured.")

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if raw_response in (None, [], {}):
            return []
        raise AdapterNotConfiguredError("Skyscanner normalization mapping is not implemented.")

    def verify_price(self, offer_id: str) -> PriceVerification:
        return PriceVerification(
            offer_id=offer_id, supplier=self.name, status=VerificationStatus.not_configured,
            checked_at=datetime.now(timezone.utc),
            message="Skyscanner price verification is not configured.",
        )
