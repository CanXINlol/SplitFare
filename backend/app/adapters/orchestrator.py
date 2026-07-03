import asyncio
import re
from dataclasses import dataclass
from datetime import date

from app.adapters.base import SupplierAdapter
from app.cache import RedisCache, flight_cache_key
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceVerification,
    SearchError,
    SearchRequest,
    Supplier,
    SupplierFailure,
    SupplierSearchOutcome,
)


SENSITIVE_VALUE = re.compile(
    r"(?i)\b(token|api[_-]?key|authorization|secret)\s*[:=]\s*[^\s,;]+"
)
BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+\-/]+=*")


def sanitize_error_message(message: str) -> str:
    sanitized = SENSITIVE_VALUE.sub(r"\1=[REDACTED]", message)
    sanitized = BEARER_VALUE.sub("Bearer [REDACTED]", sanitized)
    return sanitized[:500]


@dataclass(frozen=True)
class RouteSearchResult:
    offers: tuple[NormalizedFlightOffer, ...]
    errors: tuple[SearchError, ...]


class SupplierOrchestrator:
    def __init__(
        self,
        adapters: list[SupplierAdapter],
        supplier_timeout_seconds: float = 10,
        max_offers_per_supplier_leg: int = 30,
        cache: RedisCache | None = None,
    ):
        self.adapters = tuple(adapters)
        self.supplier_timeout_seconds = supplier_timeout_seconds
        self.max_offers_per_supplier_leg = max_offers_per_supplier_leg
        self.cache = cache

    def search(self, request: SearchRequest) -> SupplierSearchOutcome:
        offers: list[NormalizedFlightOffer] = []
        failures: list[SupplierFailure] = []
        for adapter in self.adapters:
            try:
                normalized = adapter.search_one_way(
                    request.origin,
                    request.destination,
                    request.departure_date,
                    request.passengers,
                    request.cabin,
                    request.currency,
                )
                if not all(isinstance(offer, NormalizedFlightOffer) for offer in normalized):
                    raise TypeError("Adapter returned data that was not normalized.")
                if any(offer.supplier != adapter.name for offer in normalized):
                    raise ValueError("Normalized offer supplier does not match adapter name.")
                offers.extend(normalized)
            except Exception as error:
                failures.append(SupplierFailure(
                    supplier=adapter.name,
                    error_type=type(error).__name__,
                    message=str(error),
                ))

        unique: dict[tuple[str, str], NormalizedFlightOffer] = {}
        for offer in offers:
            unique.setdefault((offer.supplier.value, offer.id), offer)
        return SupplierSearchOutcome(offers=list(unique.values()), failures=failures)

    async def _query_adapter(
        self,
        adapter: SupplierAdapter,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> RouteSearchResult:
        try:
            key = flight_cache_key(
                adapter.name,
                origin,
                destination,
                departure_date.isoformat(),
                passengers,
                cabin,
                currency,
            )
            policy = adapter.cache_policy

            def fetch() -> list[NormalizedFlightOffer]:
                return adapter.search_one_way(
                    origin,
                    destination,
                    departure_date,
                    passengers,
                    cabin,
                    currency,
                )

            def serialize(offers: list[NormalizedFlightOffer]) -> list[dict[str, object]]:
                return [offer.model_dump(mode="json") for offer in offers]

            def deserialize(payload: object) -> list[NormalizedFlightOffer]:
                if not isinstance(payload, list):
                    raise TypeError("Cached supplier response must be a list.")
                return [NormalizedFlightOffer.model_validate(item) for item in payload]

            normalized = await asyncio.wait_for(
                asyncio.to_thread(
                    self.cache.get_or_fetch if self.cache and policy.can_store else fetch,
                    key,
                    fetch,
                    policy.ttl_seconds,
                    serialize=serialize,
                    deserialize=deserialize,
                    enabled=policy.can_store,
                ) if self.cache and policy.can_store else asyncio.to_thread(
                    fetch,
                ),
                timeout=self.supplier_timeout_seconds,
            )
            if not all(isinstance(offer, NormalizedFlightOffer) for offer in normalized):
                raise TypeError("Adapter returned data that was not normalized.")
            if any(offer.supplier != adapter.name for offer in normalized):
                raise ValueError("Normalized offer supplier does not match adapter name.")
            return RouteSearchResult(
                offers=tuple(normalized[: self.max_offers_per_supplier_leg]),
                errors=(),
            )
        except TimeoutError:
            error = SearchError(
                supplier=adapter.name,
                origin=origin,
                destination=destination,
                code="supplier_timeout",
                message=f"{adapter.name.value} exceeded the supplier timeout.",
            )
        except Exception as exception:
            error = SearchError(
                supplier=adapter.name,
                origin=origin,
                destination=destination,
                code=type(exception).__name__,
                message=sanitize_error_message(str(exception)),
            )
        return RouteSearchResult(offers=(), errors=(error,))

    async def search_route(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> RouteSearchResult:
        results = await asyncio.gather(*(
            self._query_adapter(
                adapter, origin, destination, departure_date, passengers, cabin, currency
            )
            for adapter in self.adapters
        ))
        offers = tuple(offer for result in results for offer in result.offers)
        errors = tuple(error for result in results for error in result.errors)
        return RouteSearchResult(offers=offers, errors=errors)

    def verify_price(self, supplier: Supplier, offer_id: str) -> PriceVerification:
        adapter = next((item for item in self.adapters if item.name == supplier), None)
        if adapter is None:
            raise ValueError(f"Unknown supplier: {supplier.value}")
        return adapter.verify_price(offer_id)
