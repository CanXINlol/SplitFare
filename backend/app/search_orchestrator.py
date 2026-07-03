from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.adapters.orchestrator import (
    RouteSearchResult,
    SupplierOrchestrator,
    sanitize_error_message,
)
from app.cache import CANDIDATE_HUBS_TTL_SECONDS, RedisCache, candidate_hubs_cache_key
from app.models import FlightQuery, NormalizedFlightOffer, SearchError, SearchRequest


DEFAULT_CANDIDATE_HUBS = (
    "BKK", "DMK", "SIN", "KUL", "HKG", "TPE", "MNL",
    "SGN", "HAN", "ICN", "NRT", "KIX", "CAN", "SZX",
)
MAX_HUBS = 12


@dataclass(frozen=True)
class OrchestratedOffers:
    offers: tuple[NormalizedFlightOffer, ...]
    errors: tuple[SearchError, ...]
    query_plan: tuple[FlightQuery, ...]


def generate_candidate_hubs(request: SearchRequest) -> tuple[str, ...]:
    source = (
        request.candidate_hubs
        if request.candidate_hubs is not None
        else list(DEFAULT_CANDIDATE_HUBS)
    )
    unique: list[str] = []
    for hub in source:
        if hub not in {request.origin, request.destination} and hub not in unique:
            unique.append(hub)
    return tuple(unique[:MAX_HUBS])


def generate_query_plan(request: SearchRequest) -> tuple[FlightQuery, ...]:
    queries = [FlightQuery(
        origin=request.origin,
        destination=request.destination,
        departure_date=request.departure_date,
        kind="baseline",
    )]
    for hub in generate_candidate_hubs(request):
        queries.extend((
            FlightQuery(
                origin=request.origin,
                destination=hub,
                departure_date=request.departure_date,
                kind="outbound_to_hub",
                hub=hub,
            ),
            FlightQuery(
                origin=hub,
                destination=request.destination,
                departure_date=request.departure_date,
                kind="hub_to_destination",
                hub=hub,
            ),
        ))
    return tuple(queries)


class SearchOrchestrator:
    def __init__(
        self,
        supplier_orchestrator: SupplierOrchestrator,
        total_timeout_seconds: float = 30,
        cache: RedisCache | None = None,
    ):
        self.supplier_orchestrator = supplier_orchestrator
        self.total_timeout_seconds = total_timeout_seconds
        self.cache = cache

    def _cached_candidate_hubs(self, request: SearchRequest) -> tuple[str, ...]:
        if self.cache is None or request.candidate_hubs is not None:
            return generate_candidate_hubs(request)
        key = candidate_hubs_cache_key(request.origin, request.destination)
        return self.cache.get_or_fetch(
            key,
            lambda: generate_candidate_hubs(request),
            CANDIDATE_HUBS_TTL_SECONDS,
            serialize=lambda hubs: list(hubs),
            deserialize=lambda payload: tuple(str(item) for item in payload),
        )

    def _query_plan(self, request: SearchRequest) -> tuple[FlightQuery, ...]:
        queries = [FlightQuery(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            kind="baseline",
        )]
        for hub in self._cached_candidate_hubs(request):
            queries.extend((
                FlightQuery(
                    origin=request.origin,
                    destination=hub,
                    departure_date=request.departure_date,
                    kind="outbound_to_hub",
                    hub=hub,
                ),
                FlightQuery(
                    origin=hub,
                    destination=request.destination,
                    departure_date=request.departure_date,
                    kind="hub_to_destination",
                    hub=hub,
                ),
            ))
        return tuple(queries)

    async def _run_query(
        self, query: FlightQuery, request: SearchRequest
    ) -> RouteSearchResult:
        return await self.supplier_orchestrator.search_route(
            query.origin,
            query.destination,
            query.departure_date,
            request.passengers,
            request.cabin,
            request.currency,
        )

    async def collect_offers(self, request: SearchRequest) -> OrchestratedOffers:
        plan = self._query_plan(request)
        task_to_query = {
            asyncio.create_task(self._run_query(query, request)): query
            for query in plan
        }
        done, pending = await asyncio.wait(
            task_to_query,
            timeout=self.total_timeout_seconds,
        )
        offers: list[NormalizedFlightOffer] = []
        errors: list[SearchError] = []
        for task in done:
            query = task_to_query[task]
            try:
                result = task.result()
                offers.extend(result.offers)
                errors.extend(result.errors)
            except Exception as exception:
                errors.append(SearchError(
                    supplier=None,
                    origin=query.origin,
                    destination=query.destination,
                    code=type(exception).__name__,
                    message=sanitize_error_message(str(exception)),
                ))
        for task in pending:
            query = task_to_query[task]
            task.cancel()
            errors.append(SearchError(
                supplier=None,
                origin=query.origin,
                destination=query.destination,
                code="search_timeout",
                message="The route query exceeded the total search timeout.",
            ))
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        unique_offers: dict[tuple[str, str], NormalizedFlightOffer] = {}
        for offer in offers:
            unique_offers.setdefault((offer.supplier.value, offer.id), offer)
        unique_errors: dict[tuple[str | None, str, str], SearchError] = {}
        for error in errors:
            key = (
                error.supplier.value if error.supplier else None,
                error.code,
                error.message,
            )
            unique_errors.setdefault(key, error)
        return OrchestratedOffers(
            offers=tuple(unique_offers.values()),
            errors=tuple(unique_errors.values()),
            query_plan=plan,
        )
