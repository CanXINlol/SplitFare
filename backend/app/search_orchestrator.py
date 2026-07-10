from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.adapters.orchestrator import (
    RouteSearchResult,
    SupplierOrchestrator,
    sanitize_error_message,
)
from app.cache import RedisCache
from app.cities import city_service
from app.models import AirportSearchMatrix, FlightQuery, NormalizedFlightOffer, SearchCacheContext, SearchError, SearchRequest


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
    matrix: AirportSearchMatrix
    supplier_query_count: int
    supplier_query_limit: int


def generate_candidate_hubs(request: SearchRequest) -> tuple[str, ...]:
    source = (
        request.candidate_hubs
        if request.candidate_hubs is not None
        else list(DEFAULT_CANDIDATE_HUBS)
    )
    unique: list[str] = []
    for hub in source:
        if hub not in unique:
            unique.append(hub)
    return tuple(unique[:MAX_HUBS])


def generate_query_plan(request: SearchRequest) -> tuple[FlightQuery, ...]:
    matrix = city_service.build_matrix(request, generate_candidate_hubs(request))
    return tuple(matrix.query_plan)


class SearchOrchestrator:
    def __init__(
        self,
        supplier_orchestrator: SupplierOrchestrator,
        total_timeout_seconds: float = 30,
        cache: RedisCache | None = None,
        max_supplier_queries_per_search: int = 120,
    ):
        self.supplier_orchestrator = supplier_orchestrator
        self.total_timeout_seconds = total_timeout_seconds
        self.cache = cache
        self.max_supplier_queries_per_search = max(1, max_supplier_queries_per_search)

    def _matrix(self, request: SearchRequest) -> AirportSearchMatrix:
        supplier_count = max(1, len(self.supplier_orchestrator.searchable_adapters))
        max_route_queries = max(1, self.max_supplier_queries_per_search // supplier_count)
        return city_service.build_matrix(
            request,
            generate_candidate_hubs(request),
            max_route_queries=max_route_queries,
        )

    async def _run_query(
        self, query: FlightQuery, request: SearchRequest, matrix: AirportSearchMatrix
    ) -> RouteSearchResult:
        context = SearchCacheContext(
            origin_city_id=request.origin_city_id,
            destination_city_id=request.destination_city_id,
            resolved_origin_airports=[item.iata_code for item in matrix.origin_airports],
            resolved_destination_airports=[item.iata_code for item in matrix.destination_airports],
            min_gap_hours=request.min_gap_hours,
            max_gap_hours=request.max_gap_hours,
            supplier_mode="mock" if any(adapter.name.value.startswith(("Mock", "Demo", "Budget")) for adapter in self.supplier_orchestrator.searchable_adapters) else "live",
        )
        return await self.supplier_orchestrator.search_route(
            query.origin,
            query.destination,
            query.departure_date,
            request.passengers,
            request.cabin,
            request.currency,
            context,
        )

    async def collect_offers(self, request: SearchRequest) -> OrchestratedOffers:
        matrix = self._matrix(request)
        plan = tuple(matrix.query_plan)
        task_to_query = {
            asyncio.create_task(self._run_query(query, request, matrix)): query
            for query in plan
        }
        done, pending = await asyncio.wait(
            task_to_query,
            timeout=self.total_timeout_seconds,
        )
        offers: list[NormalizedFlightOffer] = []
        errors: list[SearchError] = []
        for task, query in task_to_query.items():
            if task not in done:
                continue
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
        for task, query in task_to_query.items():
            if task not in pending:
                continue
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
            errors=tuple(sorted(
                unique_errors.values(),
                key=lambda error: (
                    error.supplier.value if error.supplier else "",
                    error.code,
                    error.origin or "",
                    error.destination or "",
                ),
            )),
            query_plan=plan,
            matrix=matrix,
            supplier_query_count=len(plan) * len(self.supplier_orchestrator.searchable_adapters),
            supplier_query_limit=self.max_supplier_queries_per_search,
        )
