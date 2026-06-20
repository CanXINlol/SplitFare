from __future__ import annotations

from datetime import datetime

from app.models import (
    Itinerary,
    ItineraryType,
    MatchingRequest,
    MatchingResult,
    NormalizedFlightOffer,
    RiskLevel,
    SortOption,
)
from app.risk import assess_itinerary_risk


SAME_CITY_AIRPORT_GROUPS = (
    frozenset({"PVG", "SHA"}),
    frozenset({"NRT", "HND"}),
    frozenset({"LHR", "LGW", "STN"}),
)


def duration_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def airports_can_connect(arrival_airport: str, departure_airport: str) -> bool:
    if arrival_airport == departure_airport:
        return True
    return any(
        arrival_airport in group and departure_airport in group
        for group in SAME_CITY_AIRPORT_GROUPS
    )


def _build_itinerary(
    offers: tuple[NormalizedFlightOffer, ...],
    itinerary_type: ItineraryType,
    baseline_price: float | None,
    checked_baggage_likely_required: bool,
    visa_transit_requirement_unknown: bool,
) -> Itinerary:
    segments = [segment for offer in offers for segment in offer.segments]
    total_price = sum(offer.price_amount for offer in offers)
    is_split = itinerary_type == ItineraryType.split_ticket
    gap = duration_minutes(offers[0].arrival_at, offers[1].departure_at) if is_split else None
    cross_airport = is_split and offers[0].destination != offers[1].origin
    risk = assess_itinerary_risk(
        itinerary_type,
        list(offers),
        layover_gap_minutes=gap,
        requires_ground_transfer=cross_airport,
        checked_baggage_likely_required=checked_baggage_likely_required,
        visa_transit_requirement_unknown=visa_transit_requirement_unknown,
    )
    return Itinerary(
        id="__".join(offer.id for offer in offers),
        type=itinerary_type,
        total_price=total_price,
        currency=offers[0].currency,
        total_duration_minutes=duration_minutes(offers[0].departure_at, offers[-1].arrival_at),
        layover_airport=offers[0].destination if is_split else None,
        layover_gap_minutes=gap,
        layover_departure_airport=offers[1].origin if cross_airport else None,
        requires_ground_transfer=cross_airport,
        risk_score=risk.score,
        risk_level=risk.level,
        savings_vs_baseline=None if baseline_price is None else baseline_price - total_price,
        value_score=0,
        warnings=risk.warnings,
        segments=segments,
        offers=list(offers),
        risk_assessment=risk,
        suppliers=sorted({offer.supplier for offer in offers}, key=lambda supplier: supplier.value),
        last_checked_at=min(offer.last_checked_at for offer in offers),
        expires_at=min(offer.expires_at for offer in offers),
    )


def _with_value_scores(
    itineraries: list[Itinerary], baseline_price: float | None
) -> list[Itinerary]:
    if not itineraries:
        return []
    durations = [itinerary.total_duration_minutes for itinerary in itineraries]
    shortest, longest = min(durations), max(durations)
    duration_range = longest - shortest
    scored: list[Itinerary] = []
    for itinerary in itineraries:
        savings = itinerary.savings_vs_baseline
        savings_score = (
            max(0.0, min(1.0, savings / baseline_price))
            if savings is not None and baseline_price and baseline_price > 0
            else 0.0
        )
        risk_inverse = (100 - itinerary.risk_score) / 100
        duration_score = (
            1.0 if duration_range == 0
            else (longest - itinerary.total_duration_minutes) / duration_range
        )
        convenience_score = (
            1.0 if itinerary.type == ItineraryType.protected
            else 0.0 if itinerary.requires_ground_transfer
            else 0.5 if (itinerary.layover_gap_minutes or 0) > 720
            else 0.75
        )
        value_score = round(
            100 * (
                0.45 * savings_score
                + 0.30 * risk_inverse
                + 0.15 * duration_score
                + 0.10 * convenience_score
            ),
            2,
        )
        scored.append(itinerary.model_copy(update={"value_score": value_score}))
    return scored


def _deduplicate(itineraries: list[Itinerary]) -> list[Itinerary]:
    unique: dict[tuple[str, ...], Itinerary] = {}
    for itinerary in itineraries:
        key = tuple(offer.id for offer in itinerary.offers)
        unique.setdefault(key, itinerary)
    return list(unique.values())


def match_flight_offers(request: MatchingRequest) -> MatchingResult:
    """Pure, deterministic matcher. It never mutates request or its offers."""
    currencies = {offer.currency for offer in request.offers}
    if len(currencies) > 1:
        raise ValueError("Multiple currencies are not supported in one matching request.")

    offers = sorted(request.offers, key=lambda offer: (offer.departure_at, offer.id))
    dated = [offer for offer in offers if offer.departure_at.date() == request.departure_date]
    direct = [
        offer for offer in dated
        if offer.origin == request.origin and offer.destination == request.destination
    ]
    baseline_price = min((offer.price_amount for offer in direct), default=None)
    protected = _deduplicate([
        _build_itinerary(
            (offer,), ItineraryType.protected, baseline_price,
            request.checked_baggage_likely_required,
            request.visa_transit_requirement_unknown,
        )
        for offer in direct
    ])

    first_legs = [offer for offer in dated if offer.origin == request.origin]
    second_legs = [offer for offer in offers if offer.destination == request.destination]
    split: list[Itinerary] = []
    for first in first_legs:
        for second in second_legs:
            if first.id == second.id or not airports_can_connect(first.destination, second.origin):
                continue
            if second.departure_at <= first.arrival_at:
                continue
            gap = duration_minutes(first.arrival_at, second.departure_at)
            if request.min_gap_minutes <= gap <= request.max_gap_minutes:
                split.append(
                    _build_itinerary(
                        (first, second), ItineraryType.split_ticket, baseline_price,
                        request.checked_baggage_likely_required,
                        request.visa_transit_requirement_unknown,
                    )
                )
    split = _deduplicate(split)

    scored = _with_value_scores(protected + split, baseline_price)
    by_id = {itinerary.id: itinerary for itinerary in scored}
    protected = [by_id[itinerary.id] for itinerary in protected]
    split = [by_id[itinerary.id] for itinerary in split]
    if request.sort == SortOption.cheapest:
        ranked = sorted(
            scored,
            key=lambda itinerary: (
                itinerary.total_price,
                itinerary.total_duration_minutes,
                itinerary.risk_score,
                itinerary.id,
            ),
        )
    else:
        ranked = sorted(
            scored,
            key=lambda itinerary: (
                itinerary.risk_level == RiskLevel.extreme,
                -itinerary.value_score,
                itinerary.total_price,
                itinerary.total_duration_minutes,
                itinerary.id,
            ),
        )
    return MatchingResult(
        protected_itineraries=protected,
        split_ticket_itineraries=split,
        baseline_price=baseline_price,
        ranked_results=ranked[: request.max_results],
    )
