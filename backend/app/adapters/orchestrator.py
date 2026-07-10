import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapter
from app.cache import RedisCache, flight_cache_key
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceStatus,
    SearchError,
    SearchRequest,
    Supplier,
    SupplierError,
    SupplierFailure,
    SupplierResult,
    SupplierSearchOutcome,
    VerifyPriceResult,
)


SENSITIVE_VALUE = re.compile(
    r"(?i)\b(token|api[_-]?key|authorization|secret)\s*[:=]\s*[^\s,;]+"
)
BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+\-/]+=*")


def sanitize_error_message(message: str) -> str:
    sanitized = SENSITIVE_VALUE.sub(r"\1=[REDACTED]", message)
    sanitized = BEARER_VALUE.sub("Bearer [REDACTED]", sanitized)
    return sanitized[:500]


def supplier_error_code(exception: Exception) -> tuple[str, bool]:
    if isinstance(exception, (TimeoutError, httpx.TimeoutException)):
        return "supplier_timeout", True
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        if status == 429:
            return "supplier_rate_limited", True
        if status in {401, 403}:
            return "supplier_auth_error", False
        return "supplier_http_error", status >= 500
    if isinstance(exception, AdapterNotConfiguredError):
        return "supplier_not_configured", False
    if isinstance(exception, (TypeError, ValueError)):
        return "supplier_invalid_response", False
    return type(exception).__name__, False


@dataclass(frozen=True)
class RouteSearchResult:
    offers: tuple[NormalizedFlightOffer, ...]
    errors: tuple[SearchError, ...]
    supplier_results: tuple[SupplierResult, ...] = ()


class SupplierOrchestrator:
    def __init__(
        self,
        adapters: list[SupplierAdapter],
        supplier_timeout_seconds: float = 10,
        max_offers_per_supplier_leg: int = 30,
        cache: RedisCache | None = None,
        max_concurrent_requests: int = 8,
    ):
        self.adapters = tuple(adapters)
        self.supplier_timeout_seconds = supplier_timeout_seconds
        self.max_offers_per_supplier_leg = max_offers_per_supplier_leg
        self.cache = cache
        self.max_concurrent_requests = max(1, max_concurrent_requests)
        self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    @property
    def searchable_adapters(self) -> tuple[SupplierAdapter, ...]:
        return tuple(adapter for adapter in self.adapters if adapter.capabilities.supports_search)

    def search(self, request: SearchRequest) -> SupplierSearchOutcome:
        from app.places import place_service

        origin = place_service.resolve(request.origin_place_id).airports[0].iata_code
        destination = place_service.resolve(request.destination_place_id).airports[0].iata_code
        offers: list[NormalizedFlightOffer] = []
        failures: list[SupplierFailure] = []
        supplier_results: list[SupplierResult] = []
        for adapter in self.searchable_adapters:
            try:
                normalized = adapter.search_one_way(
                    origin,
                    destination,
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
                supplier_results.append(SupplierResult(
                    supplier=adapter.name,
                    offers=normalized,
                    errors=[],
                    capabilities=adapter.capabilities,
                    fetched_at=datetime.now(timezone.utc),
                ))
            except Exception as error:
                code, retryable = supplier_error_code(error)
                supplier_error = SupplierError(
                    supplier=adapter.name,
                    code=code,
                    message=sanitize_error_message(str(error)),
                    retryable=retryable,
                )
                failures.append(SupplierFailure(
                    supplier=adapter.name,
                    error_type=supplier_error.code,
                    message=supplier_error.message,
                ))
                supplier_results.append(SupplierResult(
                    supplier=adapter.name,
                    offers=[],
                    errors=[supplier_error],
                    capabilities=adapter.capabilities,
                    fetched_at=datetime.now(timezone.utc),
                ))

        unique: dict[tuple[str, str], NormalizedFlightOffer] = {}
        for offer in offers:
            unique.setdefault((offer.supplier.value, offer.id), offer)
        return SupplierSearchOutcome(
            offers=list(unique.values()),
            failures=failures,
            supplier_results=supplier_results,
        )

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
                return [
                    NormalizedFlightOffer.model_validate(item).model_copy(
                        update={"price_status": PriceStatus.cached}
                    )
                    for item in payload
                ]

            async with self._semaphore:
                normalized = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.cache.get_or_fetch,
                        key,
                        fetch,
                        policy.ttl_seconds,
                        serialize=serialize,
                        deserialize=deserialize,
                        enabled=policy.can_store,
                    ) if self.cache and policy.can_store else asyncio.to_thread(fetch),
                    timeout=self.supplier_timeout_seconds,
                )
            if not all(isinstance(offer, NormalizedFlightOffer) for offer in normalized):
                raise TypeError("Adapter returned data that was not normalized.")
            if any(offer.supplier != adapter.name for offer in normalized):
                raise ValueError("Normalized offer supplier does not match adapter name.")
            return RouteSearchResult(
                offers=tuple(normalized[: self.max_offers_per_supplier_leg]),
                errors=(),
                supplier_results=(SupplierResult(
                    supplier=adapter.name,
                    offers=list(normalized[: self.max_offers_per_supplier_leg]),
                    errors=[],
                    capabilities=adapter.capabilities,
                    fetched_at=datetime.now(timezone.utc),
                ),),
            )
        except (TimeoutError, httpx.TimeoutException):
            error = SearchError(
                supplier=adapter.name,
                origin=origin,
                destination=destination,
                code="supplier_timeout",
                message=f"{adapter.name.value} exceeded the supplier timeout.",
            )
            supplier_error = SupplierError(
                supplier=adapter.name,
                code=error.code,
                message=error.message,
                retryable=True,
            )
        except Exception as exception:
            code, retryable = supplier_error_code(exception)
            error = SearchError(
                supplier=adapter.name,
                origin=origin,
                destination=destination,
                code=code,
                message=sanitize_error_message(str(exception)),
            )
            supplier_error = SupplierError(
                supplier=adapter.name,
                code=error.code,
                message=error.message,
                retryable=retryable,
            )
        return RouteSearchResult(
            offers=(),
            errors=(error,),
            supplier_results=(SupplierResult(
                supplier=adapter.name,
                offers=[],
                errors=[supplier_error],
                capabilities=adapter.capabilities,
                fetched_at=datetime.now(timezone.utc),
            ),),
        )

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
            for adapter in self.searchable_adapters
        ))
        offers = tuple(offer for result in results for offer in result.offers)
        errors = tuple(error for result in results for error in result.errors)
        supplier_results = tuple(item for result in results for item in result.supplier_results)
        return RouteSearchResult(offers=offers, errors=errors, supplier_results=supplier_results)

    def verify_price(self, supplier: Supplier, offer_id: str) -> VerifyPriceResult:
        adapter = next((item for item in self.adapters if item.name == supplier), None)
        if adapter is None:
            raise ValueError(f"Unknown supplier: {supplier.value}")
        if not adapter.capabilities.supports_price_verify:
            return adapter.verify_price_result(offer_id)
        return adapter.verify_price_result(offer_id)

    def capabilities_for(self, supplier: Supplier):
        adapter = next((item for item in self.adapters if item.name == supplier), None)
        return adapter.capabilities if adapter else None
