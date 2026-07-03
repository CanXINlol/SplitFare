from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.adapters.mock_supplier import MockFlightSupplier
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceVerification,
    RiskAssessment,
    RiskLevel,
    SearchRequest,
    Segment,
    Supplier,
    VerificationStatus,
)


NOW = datetime(2026, 8, 12, 0, tzinfo=timezone.utc)


def valid_offer_data() -> dict[str, object]:
    departure = NOW + timedelta(hours=7)
    arrival = departure + timedelta(hours=9)
    segment = Segment(
        id="segment-1",
        origin="MEL",
        destination="BKK",
        departure_at=departure,
        arrival_at=arrival,
        airline="TG",
        operating_airline="TG",
        flight_number="TG466",
    )
    return {
        "id": "offer-1",
        "supplier": Supplier.mock_sky,
        "origin": "MEL",
        "destination": "BKK",
        "departure_at": departure,
        "arrival_at": arrival,
        "airline": "TG",
        "operating_airline": "TG",
        "flight_number": "TG466",
        "price_amount": 390,
        "currency": "AUD",
        "cabin": Cabin.economy,
        "baggage_included": True,
        "booking_url": None,
        "raw_payload": {"fixture": "segment-1"},
        "last_checked_at": NOW,
        "expires_at": NOW + timedelta(hours=2),
        "segments": [segment],
    }


@pytest.mark.parametrize(
    "required_field",
    ["price_amount", "currency", "departure_at", "arrival_at", "last_checked_at", "expires_at"],
)
def test_offer_rejects_missing_price_currency_or_time(required_field: str) -> None:
    data = valid_offer_data()
    data.pop(required_field)
    with pytest.raises(ValidationError):
        NormalizedFlightOffer.model_validate(data)


def test_offer_rejects_non_positive_price_and_invalid_currency() -> None:
    for patch in ({"price_amount": 0}, {"currency": "AU"}):
        with pytest.raises(ValidationError):
            NormalizedFlightOffer.model_validate(valid_offer_data() | patch)


def test_offer_rejects_naive_or_inverted_times() -> None:
    data = valid_offer_data()
    naive_departure = data["departure_at"].replace(tzinfo=None)  # type: ignore[union-attr]
    with pytest.raises(ValidationError):
        NormalizedFlightOffer.model_validate(data | {"departure_at": naive_departure})
    with pytest.raises(ValidationError):
        Segment.model_validate({
            "id": "bad", "origin": "MEL", "destination": "BKK",
            "departure_at": NOW + timedelta(hours=2), "arrival_at": NOW + timedelta(hours=1),
            "airline": "TG", "operating_airline": "TG", "flight_number": "TG466",
        })


def test_offer_rejects_segment_endpoint_mismatch() -> None:
    with pytest.raises(ValidationError, match="endpoints"):
        NormalizedFlightOffer.model_validate(valid_offer_data() | {"destination": "PVG"})


def test_risk_assessment_rejects_level_score_mismatch() -> None:
    with pytest.raises(ValidationError, match="does not match"):
        RiskAssessment(score=85, level=RiskLevel.medium, warnings=[])


def test_price_verification_never_confirms_expired_or_unavailable_price() -> None:
    unavailable = PriceVerification(
        offerId="offer-1",
        supplier=Supplier.mock_sky,
        status=VerificationStatus.unavailable,
        checkedAt=NOW,
        message="not found",
    )
    assert unavailable.is_confirmed is False
    with pytest.raises(ValidationError, match="expires_at"):
        PriceVerification(
            offerId="offer-1",
            supplier=Supplier.mock_sky,
            status=VerificationStatus.verified,
            priceAmount=100,
            currency="AUD",
            checkedAt=NOW,
            expiresAt=NOW,
            message="bad expiry",
        )


def test_search_request_normalizes_iata_and_validates_gap() -> None:
    request = SearchRequest(
        origin=" mel ", destination="pvg", departureDate="2026-08-12",
        minGapHours=3, maxGapHours=12, passengers=1, cabin="economy",
    )
    assert (request.origin_place_id, request.destination_place_id) == ("airport:MEL", "airport:PVG")
    with pytest.raises(ValidationError, match="max_gap_hours"):
        SearchRequest(
            originPlaceId="airport:MEL", destinationPlaceId="airport:PVG", departureDate="2026-08-12",
            minGapHours=10, maxGapHours=3, passengers=1, cabin="economy",
        )


def test_all_mock_data_is_normalized() -> None:
    request = SearchRequest(
        originPlaceId="airport:MEL", destinationPlaceId="airport:PVG", departureDate="2026-08-12",
        minGapHours=3, maxGapHours=12, passengers=1, cabin="economy",
    )
    offers = MockFlightSupplier().search(request)
    assert offers
    assert all(isinstance(offer, NormalizedFlightOffer) for offer in offers)
    assert all(offer.raw_payload.get("fixture") for offer in offers)
