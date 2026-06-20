from uuid import uuid4

from app.matching import match_flight_offers
from app.models import (
    MatchingRequest,
    SearchRequest,
    SearchResponse,
    SearchResults,
    SearchStatus,
    SupplierFailure,
)
from app.search_orchestrator import SearchOrchestrator


class SearchService:
    def __init__(self, orchestrator: SearchOrchestrator):
        self.orchestrator = orchestrator

    async def search(self, request: SearchRequest) -> SearchResponse:
        supplier_result = await self.orchestrator.collect_offers(request)
        result = match_flight_offers(MatchingRequest(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            min_gap_minutes=round(request.min_gap_hours * 60),
            max_gap_minutes=round(request.max_gap_hours * 60),
            max_results=request.max_results,
            offers=supplier_result.offers,
            sort=request.sort,
            checked_baggage_likely_required=request.checked_baggage_likely_required,
            visa_transit_requirement_unknown=request.visa_transit_requirement_unknown,
        ))
        baseline = min(result.protected_itineraries, key=lambda item: item.total_price, default=None)
        cheapest = min(result.split_ticket_itineraries, key=lambda item: item.total_price, default=None)
        safest = min(
            result.split_ticket_itineraries,
            key=lambda item: (item.risk_score, item.total_price),
            default=None,
        )
        status = (
            SearchStatus.empty if not result.ranked_results
            else SearchStatus.partial if supplier_result.errors
            else SearchStatus.complete
        )
        explanation = (
            "No itineraries matched the route, date and connection-gap constraints."
            if status == SearchStatus.empty
            else "Results are partial because one or more supplier queries failed or timed out."
            if status == SearchStatus.partial
            else "Search completed successfully."
        )
        search_results = SearchResults(
            protected_itineraries=result.protected_itineraries,
            split_ticket_itineraries=result.split_ticket_itineraries,
            baseline_price=result.baseline_price,
            ranked_results=result.ranked_results,
        )
        return SearchResponse(
            search_id=str(uuid4()),
            status=status,
            results=search_results,
            errors=list(supplier_result.errors),
            explanation=explanation,
            baseline=baseline,
            cheapest_split=cheapest,
            safest_split=safest,
            ranked=result.ranked_results,
            protected_itineraries=result.protected_itineraries,
            split_ticket_itineraries=result.split_ticket_itineraries,
            baseline_price=result.baseline_price,
            ranked_results=result.ranked_results,
            supplier_failures=[
                SupplierFailure(
                    supplier=error.supplier,
                    error_type=error.code,
                    message=error.message,
                )
                for error in supplier_result.errors
                if error.supplier is not None
            ],
            disclaimer="Fictional mock fares only. Not live availability and not a guarantee of transit, baggage, visa or entry feasibility.",
        )
