from datetime import date, datetime, timedelta, timezone

import pytest

from app.matching import match_flight_offers
from app.models import (
    Cabin,
    ItineraryType,
    MatchingRequest,
    NormalizedFlightOffer,
    RiskLevel,
    Segment,
    SortOption,
    Supplier,
)


DAY = datetime(2026, 8, 12, tzinfo=timezone.utc)


def offer(
    offer_id: str,
    origin: str,
    destination: str,
    departure: datetime,
    duration: int,
    price: float,
    currency: str = "AUD",
    baggage: bool | None = True,
) -> NormalizedFlightOffer:
    arrival = departure + timedelta(minutes=duration)
    segment = Segment(
        id=f"segment-{offer_id}", origin=origin, destination=destination,
        departure_at=departure, arrival_at=arrival, airline="ZZ",
        operating_airline="ZZ", flight_number=f"ZZ{offer_id[-2:]}",
    )
    return NormalizedFlightOffer(
        id=offer_id, supplier=Supplier.mock_sky, origin=origin, destination=destination,
        departure_at=departure, arrival_at=arrival, airline="ZZ", operating_airline="ZZ",
        flight_number=f"ZZ{offer_id[-2:]}", price_amount=price, currency=currency,
        cabin=Cabin.economy, baggage_included=baggage, raw_payload={"id": offer_id},
        last_checked_at=DAY, expires_at=DAY + timedelta(hours=2), segments=[segment],
    )


def standard_offers() -> tuple[NormalizedFlightOffer, ...]:
    return (
        offer("direct-01", "MEL", "PVG", DAY + timedelta(hours=8), 620, 1000),
        offer("first-01", "MEL", "BKK", DAY + timedelta(hours=6), 540, 380),
        offer("second-01", "BKK", "PVG", DAY + timedelta(hours=19), 250, 320),
    )


def request(
    offers: tuple[NormalizedFlightOffer, ...] | None = None,
    minimum: int = 180,
    maximum: int = 720,
    max_results: int = 20,
    sort: SortOption = SortOption.value,
    destination: str = "PVG",
) -> MatchingRequest:
    return MatchingRequest(
        origin="MEL", destination=destination, departure_date=date(2026, 8, 12),
        min_gap_minutes=minimum, max_gap_minutes=maximum, max_results=max_results,
        offers=offers if offers is not None else standard_offers(), sort=sort,
    )


def test_direct_offer_becomes_protected_baseline() -> None:
    result = match_flight_offers(request())
    assert result.baseline_price == 1000
    assert len(result.protected_itineraries) == 1
    assert result.protected_itineraries[0].type == ItineraryType.protected


def test_valid_same_airport_gap_creates_split_ticket() -> None:
    result = match_flight_offers(request())
    assert len(result.split_ticket_itineraries) == 1
    assert result.split_ticket_itineraries[0].layover_gap_minutes == 240


def test_second_departure_must_be_after_first_arrival() -> None:
    first = offer("first-01", "MEL", "BKK", DAY + timedelta(hours=6), 540, 300)
    second = offer("second-01", "BKK", "PVG", first.arrival_at, 200, 300)
    assert not match_flight_offers(request((first, second), 0, 600)).split_ticket_itineraries


def test_gap_below_minimum_is_rejected() -> None:
    assert not match_flight_offers(request(minimum=241)).split_ticket_itineraries


def test_gap_above_maximum_is_rejected() -> None:
    assert not match_flight_offers(request(maximum=239)).split_ticket_itineraries


def test_minimum_gap_boundary_is_inclusive() -> None:
    assert len(match_flight_offers(request(minimum=240)).split_ticket_itineraries) == 1


def test_maximum_gap_boundary_is_inclusive() -> None:
    assert len(match_flight_offers(request(maximum=240)).split_ticket_itineraries) == 1


def test_overnight_layover_is_retained_and_warned() -> None:
    first = offer("first-01", "MEL", "BKK", DAY + timedelta(hours=6), 540, 300)
    second = offer("second-01", "BKK", "PVG", DAY + timedelta(days=1, hours=8), 200, 300)
    itinerary = match_flight_offers(request((first, second), 180, 1200)).split_ticket_itineraries[0]
    assert itinerary.layover_gap_minutes == 1020
    assert any("overnight" in warning.lower() for warning in itinerary.warnings)


def test_same_airport_layover_does_not_require_ground_transfer() -> None:
    itinerary = match_flight_offers(request()).split_ticket_itineraries[0]
    assert itinerary.layover_airport == "BKK"
    assert itinerary.layover_departure_airport is None
    assert itinerary.requires_ground_transfer is False


def test_cross_airport_layover_is_high_risk() -> None:
    offers = (
        offer("first-01", "MEL", "PVG", DAY + timedelta(hours=5), 600, 300),
        offer("second-01", "SHA", "LAX", DAY + timedelta(hours=19), 700, 400),
    )
    itinerary = match_flight_offers(request(offers, 180, 600, destination="LAX")).split_ticket_itineraries[0]
    assert itinerary.requires_ground_transfer is True
    assert itinerary.layover_departure_airport == "SHA"
    assert itinerary.risk_level in {RiskLevel.high, RiskLevel.extreme}
    assert any("ground transfer" in warning.lower() for warning in itinerary.warnings)


def test_unrelated_airports_cannot_connect() -> None:
    offers = (
        offer("first-01", "MEL", "BKK", DAY + timedelta(hours=5), 500, 300),
        offer("second-01", "SIN", "PVG", DAY + timedelta(hours=18), 300, 300),
    )
    assert not match_flight_offers(request(offers)).split_ticket_itineraries


def test_no_baseline_sets_savings_to_null() -> None:
    offers = standard_offers()[1:]
    result = match_flight_offers(request(offers))
    assert result.baseline_price is None
    assert result.split_ticket_itineraries[0].savings_vs_baseline is None


def test_multiple_currencies_are_rejected() -> None:
    offers = standard_offers() + (
        offer("other-01", "MEL", "SIN", DAY + timedelta(hours=4), 400, 200, "USD"),
    )
    with pytest.raises(ValueError, match="Multiple currencies"):
        match_flight_offers(request(offers))


def test_total_price_duration_and_savings_are_calculated() -> None:
    itinerary = match_flight_offers(request()).split_ticket_itineraries[0]
    assert itinerary.total_price == 700
    assert itinerary.total_duration_minutes == 1030
    assert itinerary.savings_vs_baseline == 300


def test_default_ranking_uses_value_score_not_pure_price() -> None:
    offers = (
        offer("direct-01", "MEL", "LAX", DAY + timedelta(hours=8), 600, 1000),
        offer("first-01", "MEL", "PVG", DAY + timedelta(hours=1), 600, 50, baggage=None),
        offer("second-01", "SHA", "LAX", DAY + timedelta(days=1, hours=8), 600, 50, baggage=False),
    )
    result = match_flight_offers(request(offers, 180, 1800, destination="LAX"))
    assert result.ranked_results[0].type == ItineraryType.protected
    assert result.split_ticket_itineraries[0].risk_level == RiskLevel.extreme
    assert result.ranked_results[0].total_price > result.split_ticket_itineraries[0].total_price


def test_cheapest_sort_orders_only_by_total_price_first() -> None:
    offers = (
        offer("direct-01", "MEL", "LAX", DAY + timedelta(hours=8), 600, 1000),
        offer("first-01", "MEL", "PVG", DAY + timedelta(hours=1), 600, 50, baggage=None),
        offer("second-01", "SHA", "LAX", DAY + timedelta(days=1, hours=8), 600, 50, baggage=False),
    )
    result = match_flight_offers(request(offers, 180, 1800, sort=SortOption.cheapest, destination="LAX"))
    assert result.ranked_results[0].total_price == 100
    assert result.ranked_results[0].risk_level == RiskLevel.extreme


def test_duplicate_offer_inputs_do_not_duplicate_itineraries() -> None:
    direct, first, second = standard_offers()
    result = match_flight_offers(request((direct, direct, first, first, second, second)))
    assert len(result.protected_itineraries) == 1
    assert len(result.split_ticket_itineraries) == 1
    assert len({item.id for item in result.ranked_results}) == len(result.ranked_results)


def test_ranked_results_respect_max_results() -> None:
    assert len(match_flight_offers(request(max_results=1)).ranked_results) == 1


def test_same_input_produces_stable_output() -> None:
    matching_request = request()
    first = match_flight_offers(matching_request).model_dump(mode="json")
    second = match_flight_offers(matching_request).model_dump(mode="json")
    assert first == second


def test_first_leg_must_depart_on_requested_date() -> None:
    direct, first, second = standard_offers()
    next_day_first = offer(
        first.id, first.origin, first.destination,
        first.departure_at + timedelta(days=1), 540, first.price_amount,
    )
    result = match_flight_offers(request((direct, next_day_first, second)))
    assert not result.split_ticket_itineraries
