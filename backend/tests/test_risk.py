from datetime import datetime, timedelta, timezone

from app.models import (
    Cabin,
    ItineraryType,
    NormalizedFlightOffer,
    RiskLevel,
    Segment,
    Supplier,
)
from app.risk import (
    BAGGAGE_WARNING,
    CROSS_AIRPORT_WARNING,
    MISSED_CONNECTION_WARNING,
    OVERNIGHT_WARNING,
    SELF_TRANSFER_WARNING,
    VISA_WARNING,
    assess_itinerary_risk,
)


DAY = datetime(2026, 8, 12, tzinfo=timezone.utc)


def make_offer(
    offer_id: str,
    origin: str,
    destination: str,
    departure: datetime,
    arrival: datetime,
    *,
    supplier: Supplier = Supplier.mock_sky,
    airline: str = "ZZ",
    baggage: bool | None = True,
) -> NormalizedFlightOffer:
    segment = Segment(
        id=f"segment-{offer_id}", origin=origin, destination=destination,
        departure_at=departure, arrival_at=arrival, airline=airline,
        operating_airline=airline, flight_number=f"{airline}101",
    )
    return NormalizedFlightOffer(
        id=offer_id, supplier=supplier, origin=origin, destination=destination,
        departure_at=departure, arrival_at=arrival, airline=airline,
        operating_airline=airline, flight_number=f"{airline}101",
        price_amount=300, currency="AUD", cabin=Cabin.economy,
        baggage_included=baggage, raw_payload={}, last_checked_at=DAY,
        expires_at=DAY + timedelta(hours=2), segments=[segment],
    )


def standard_split(**second_overrides: object) -> list[NormalizedFlightOffer]:
    first = make_offer(
        "first", "MEL", "BKK", DAY + timedelta(hours=8), DAY + timedelta(hours=10)
    )
    defaults: dict[str, object] = {
        "supplier": Supplier.mock_sky,
        "airline": "ZZ",
        "baggage": True,
    }
    defaults.update(second_overrides)
    second = make_offer(
        "second", "BKK", "PVG", DAY + timedelta(hours=20), DAY + timedelta(hours=22),
        **defaults,  # type: ignore[arg-type]
    )
    return [first, second]


def assess_split(
    gap: int = 600,
    offers: list[NormalizedFlightOffer] | None = None,
    **context: bool,
):
    return assess_itinerary_risk(
        ItineraryType.split_ticket,
        offers or standard_split(),
        layover_gap_minutes=gap,
        visa_transit_requirement_unknown=False,
        **context,
    )


def test_protected_base_score_is_ten() -> None:
    result = assess_itinerary_risk(
        ItineraryType.protected, [standard_split()[0]],
        visa_transit_requirement_unknown=False,
    )
    assert (result.score, result.level) == (10, RiskLevel.low)


def test_split_base_score_and_self_transfer_warnings() -> None:
    result = assess_split()
    assert (result.score, result.level) == (45, RiskLevel.medium)
    assert SELF_TRANSFER_WARNING in result.warnings
    assert MISSED_CONNECTION_WARNING in result.warnings


def test_gap_under_180_adds_35() -> None:
    assert assess_split(179).score == 80


def test_gap_from_180_through_300_adds_20() -> None:
    assert assess_split(180).score == 65
    assert assess_split(300).score == 65


def test_gap_from_301_through_480_adds_10() -> None:
    assert assess_split(301).score == 55
    assert assess_split(480).score == 55


def test_gap_from_481_through_720_adds_nothing() -> None:
    assert assess_split(481).score == 45
    assert assess_split(720).score == 45


def test_gap_over_720_adds_8() -> None:
    result = assess_split(721)
    assert result.score == 53
    assert any("more than 12 hours" in warning for warning in result.warnings)


def test_overnight_layover_adds_12_and_warning() -> None:
    offers = [
        make_offer("first", "MEL", "BKK", DAY + timedelta(hours=20), DAY + timedelta(hours=23)),
        make_offer("second", "BKK", "PVG", DAY + timedelta(days=1, hours=1), DAY + timedelta(days=1, hours=5)),
    ]
    result = assess_split(120, offers)
    assert result.score == 97  # base 45 + short 35 + overnight 12 + early/late 5
    assert OVERNIGHT_WARNING in result.warnings


def test_cross_airport_transfer_adds_35_and_warning() -> None:
    result = assess_split(requires_ground_transfer=True)
    assert result.score == 80
    assert CROSS_AIRPORT_WARNING in result.warnings


def test_unknown_baggage_adds_10() -> None:
    offers = standard_split(baggage=None)
    result = assess_split(offers=offers)
    assert result.score == 55
    assert any("Baggage inclusion is unknown" in warning for warning in result.warnings)


def test_checked_baggage_likely_required_adds_15() -> None:
    result = assess_split(checked_baggage_likely_required=True)
    assert result.score == 60
    assert BAGGAGE_WARNING in result.warnings


def test_different_supplier_adds_10() -> None:
    assert assess_split(offers=standard_split(supplier=Supplier.demo_air)).score == 55


def test_different_airline_adds_8() -> None:
    assert assess_split(offers=standard_split(airline="YY")).score == 53


def test_low_cost_carrier_adds_8() -> None:
    offers = [
        make_offer("first", "MEL", "BKK", DAY + timedelta(hours=8), DAY + timedelta(hours=10), airline="D7"),
        make_offer("second", "BKK", "PVG", DAY + timedelta(hours=20), DAY + timedelta(hours=22), airline="D7"),
    ]
    result = assess_split(offers=offers)
    assert result.score == 53
    assert any("low-cost carrier" in warning for warning in result.warnings)


def test_unknown_visa_or_transit_requirement_adds_15() -> None:
    result = assess_itinerary_risk(
        ItineraryType.protected, [standard_split()[0]],
        visa_transit_requirement_unknown=True,
    )
    assert result.score == 25
    assert VISA_WARNING in result.warnings


def test_departure_before_6am_adds_5() -> None:
    early = make_offer(
        "early", "MEL", "PVG", DAY + timedelta(hours=5), DAY + timedelta(hours=15)
    )
    result = assess_itinerary_risk(
        ItineraryType.protected, [early], visa_transit_requirement_unknown=False
    )
    assert result.score == 15


def test_score_is_capped_at_100_and_becomes_extreme() -> None:
    offers = standard_split(supplier=Supplier.demo_air, airline="D7", baggage=None)
    result = assess_itinerary_risk(
        ItineraryType.split_ticket, offers, layover_gap_minutes=100,
        requires_ground_transfer=True, checked_baggage_likely_required=True,
        visa_transit_requirement_unknown=True,
    )
    assert (result.score, result.level) == (100, RiskLevel.extreme)


def test_warning_list_does_not_claim_visa_or_baggage_guarantees() -> None:
    result = assess_itinerary_risk(
        ItineraryType.split_ticket, standard_split(), layover_gap_minutes=600,
        checked_baggage_likely_required=True, visa_transit_requirement_unknown=True,
    )
    joined = " ".join(result.warnings).lower()
    assert "may need" in joined
    assert "guaranteed" not in joined
