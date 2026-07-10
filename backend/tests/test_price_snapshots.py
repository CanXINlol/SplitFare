from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceSnapshot,
    SearchRequest,
    Segment,
    Supplier,
    VerificationStatus,
)
from app.price_snapshots import (
    CREATE_PRICE_SNAPSHOT_TABLE_SQL,
    PriceSnapshotRecorder,
    build_price_snapshot,
    price_snapshot_columns,
)


NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def search_request() -> SearchRequest:
    return SearchRequest(
        originPlaceId="airport:MEL",
        destinationPlaceId="airport:PVG",
        departureDate=date(2026, 8, 12),
        minGapHours=3,
        maxGapHours=12,
        passengers=1,
        cabin="economy",
    )


def offer(offer_id: str = "offer-1") -> NormalizedFlightOffer:
    departure = NOW + timedelta(hours=8)
    arrival = departure + timedelta(hours=10)
    segment = Segment(
        id=f"segment-{offer_id}",
        origin="MEL",
        destination="PVG",
        departure_at=departure,
        arrival_at=arrival,
        airline="MU",
        operating_airline="MU",
        flight_number="MU740",
    )
    return NormalizedFlightOffer(
        id=offer_id,
        supplier=Supplier.mock_sky,
        origin="MEL",
        destination="PVG",
        departure_at=departure,
        arrival_at=arrival,
        airline="MU",
        operating_airline="MU",
        flight_number="MU740",
        price_amount=1120,
        currency="AUD",
        cabin=Cabin.economy,
        baggage_included=True,
        booking_url=None,
        raw_payload={"fixture": offer_id},
        last_checked_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        segments=[segment],
        protected_connection=True,
    )


def test_price_snapshot_schema_contains_required_columns() -> None:
    columns = price_snapshot_columns()
    for column in (
        "offer_id",
        "supplier",
        "price_amount",
        "currency",
        "last_checked_at",
        "expires_at",
        "verification_status",
    ):
        assert column in columns
        assert column in CREATE_PRICE_SNAPSHOT_TABLE_SQL


def test_build_price_snapshot_from_normalized_offer() -> None:
    snapshot = build_price_snapshot(
        search_id="search-1",
        request=search_request(),
        offer=offer(),
        created_at=NOW,
        cache_key="flight:MockSky:MEL:PVG:2026-08-12:1:economy:AUD",
    )
    assert snapshot.verification_status == VerificationStatus.verified
    assert snapshot.last_checked_at == NOW
    assert snapshot.expires_at == NOW + timedelta(minutes=5)
    assert snapshot.cache_key.startswith("flight:")


def test_expired_price_snapshot_cannot_be_recorded_as_verified() -> None:
    with pytest.raises(ValidationError, match="expired prices"):
        PriceSnapshot(
            id="snapshot-1",
            searchId="search-1",
            offerId="offer-1",
            supplier=Supplier.mock_sky,
            origin="MEL",
            destination="PVG",
            departureDate=date(2026, 8, 12),
            passengers=1,
            cabin=Cabin.economy,
            priceAmount=1120,
            currency="AUD",
            lastCheckedAt=NOW,
            expiresAt=NOW + timedelta(minutes=5),
            verificationStatus=VerificationStatus.verified,
            createdAt=NOW + timedelta(minutes=6),
        )


def test_snapshot_recorder_deduplicates_offer_ids_per_supplier() -> None:
    recorder = PriceSnapshotRecorder()
    snapshots = recorder.record_offers(
        search_id="search-1",
        request=search_request(),
        offers=[offer("offer-1"), offer("offer-1")],
        created_at=NOW,
    )
    assert len(snapshots) == 1
    assert len(recorder.snapshots) == 1
