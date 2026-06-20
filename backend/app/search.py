from app.adapters.base import FlightSupplier
from app.matching import match_flight_offers
from app.models import (
    MatchingRequest,
    SearchRequest,
    SearchResponse,
)


class SearchService:
    def __init__(self, supplier: FlightSupplier):
        self.supplier = supplier

    def search(self, request: SearchRequest) -> SearchResponse:
        offers = self.supplier.search(request)
        priced_offers = tuple(
            offer.model_copy(update={"price_amount": offer.price_amount * request.passengers})
            for offer in offers
        )
        result = match_flight_offers(MatchingRequest(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            min_gap_minutes=round(request.min_gap_hours * 60),
            max_gap_minutes=round(request.max_gap_hours * 60),
            max_results=request.max_results,
            offers=priced_offers,
            sort=request.sort,
            checked_baggage_likely_required=request.checked_baggage_likely_required,
            visa_transit_requirement_unknown=request.visa_transit_requirement_unknown,
        ))
        if not result.ranked_results:
            raise ValueError("No matching itineraries are available for this mock route.")
        baseline = min(result.protected_itineraries, key=lambda item: item.total_price, default=None)
        cheapest = min(result.split_ticket_itineraries, key=lambda item: item.total_price, default=None)
        safest = min(
            result.split_ticket_itineraries,
            key=lambda item: (item.risk_score, item.total_price),
            default=None,
        )
        return SearchResponse(
            baseline=baseline,
            cheapest_split=cheapest,
            safest_split=safest,
            ranked=result.ranked_results,
            protected_itineraries=result.protected_itineraries,
            split_ticket_itineraries=result.split_ticket_itineraries,
            baseline_price=result.baseline_price,
            ranked_results=result.ranked_results,
            disclaimer="Fictional mock fares only. Not live availability and not a guarantee of transit, baggage, visa or entry feasibility.",
        )
