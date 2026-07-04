from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any

from app.cache import CachePolicy, default_supplier_cache_policy
from app.models import (
    Cabin,
    FlightSlice,
    NormalizedFlightOffer,
    PriceVerification,
    SupplierCapabilities,
    Supplier,
    VerificationStatus,
    VerifyPriceResult,
)


class SupplierAdapterError(RuntimeError):
    pass


class AdapterNotConfiguredError(SupplierAdapterError):
    pass


class UnsupportedSupplierCapabilityError(SupplierAdapterError):
    pass


class SupplierAdapter(ABC):
    """Server-only boundary implemented by every authorised flight data source."""

    @property
    @abstractmethod
    def name(self) -> Supplier:
        raise NotImplementedError

    @property
    def display_name(self) -> str:
        return self.name.value

    @property
    def capabilities(self) -> SupplierCapabilities:
        return SupplierCapabilities()

    @property
    def cache_policy(self) -> CachePolicy:
        return default_supplier_cache_policy(self.name)

    def search_one_way(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> list[NormalizedFlightOffer]:
        raw_response = self._fetch_one_way(
            origin, destination, departure_date, passengers, cabin, currency
        )
        return self.normalize(raw_response)

    @abstractmethod
    def _fetch_one_way(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> Any:
        raise NotImplementedError

    def search_multi_city(
        self,
        slices: list[FlightSlice],
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> list[NormalizedFlightOffer]:
        raw_response = self._fetch_multi_city(slices, passengers, cabin, currency)
        return self.normalize(raw_response)

    def _fetch_multi_city(
        self,
        slices: list[FlightSlice],
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> Any:
        raise UnsupportedSupplierCapabilityError(
            f"{self.name.value} does not support multi-city search yet."
        )

    @abstractmethod
    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        raise NotImplementedError

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        return VerifyPriceResult(
            offer_id=offer_id,
            supplier=self.name,
            status=VerificationStatus.unsupported,
            supported=False,
            checked_at=datetime.now(timezone.utc),
            message=f"{self.name.value} does not support price verification.",
        )

    def verify_price(self, offer_id: str) -> PriceVerification:
        return self.verify_price_result(offer_id)
