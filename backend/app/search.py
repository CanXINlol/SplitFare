import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.booking_options import attach_booking_options
from app.matching import match_flight_offers
from app.models import (
    MatchingRequest,
    SearchRequest,
    SearchResponse,
    SearchResults,
    SearchStatus,
    SupplierFailure,
)
from app.price_snapshots import PriceSnapshotRecorder
from app.repositories import SearchPersistenceService
from app.search_orchestrator import SearchOrchestrator


logger = logging.getLogger("splitfare.persistence")


class SearchService:
    def __init__(
        self,
        orchestrator: SearchOrchestrator,
        price_snapshot_recorder: PriceSnapshotRecorder | None = None,
        persistence_service: SearchPersistenceService | None = None,
    ):
        self.orchestrator = orchestrator
        self.price_snapshot_recorder = price_snapshot_recorder or PriceSnapshotRecorder()
        self.persistence_service = persistence_service

    async def search(self, request: SearchRequest) -> SearchResponse:
        search_id = str(uuid4())
        supplier_result = await self.orchestrator.collect_offers(request)
        self.price_snapshot_recorder.record_offers(
            search_id=search_id,
            request=request,
            offers=list(supplier_result.offers),
            created_at=datetime.now(timezone.utc),
        )
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
        all_with_options = attach_booking_options(
            request,
            result.protected_itineraries
            + result.split_ticket_itineraries
            + result.ranked_results
            + ([baseline] if baseline else [])
            + ([cheapest] if cheapest else [])
            + ([safest] if safest else []),
        )
        by_id = {itinerary.id: itinerary for itinerary in all_with_options}
        protected_itineraries = [by_id[itinerary.id] for itinerary in result.protected_itineraries]
        split_ticket_itineraries = [by_id[itinerary.id] for itinerary in result.split_ticket_itineraries]
        ranked_results = [by_id[itinerary.id] for itinerary in result.ranked_results]
        baseline = by_id.get(baseline.id) if baseline else None
        cheapest = by_id.get(cheapest.id) if cheapest else None
        safest = by_id.get(safest.id) if safest else None
        status = (
            SearchStatus.empty if not ranked_results
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
            protected_itineraries=protected_itineraries,
            split_ticket_itineraries=split_ticket_itineraries,
            baseline_price=result.baseline_price,
            ranked_results=ranked_results,
        )
        response = SearchResponse(
            search_id=search_id,
            status=status,
            results=search_results,
            errors=list(supplier_result.errors),
            explanation=explanation,
            baseline=baseline,
            cheapest_split=cheapest,
            safest_split=safest,
            ranked=ranked_results,
            protected_itineraries=protected_itineraries,
            split_ticket_itineraries=split_ticket_itineraries,
            baseline_price=result.baseline_price,
            ranked_results=ranked_results,
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
        if self.persistence_service is not None:
            try:
                self.persistence_service.persist_search(request, response)
            except Exception as exception:
                logger.exception("persistence.search_failed search_id=%s reason=%s", search_id, type(exception).__name__)
        return response
