import asyncio
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.db_models  # noqa: F401
from app.adapters.mock_supplier import build_mock_orchestrator
from app.db import Base
from app.db_models import (
    AirportRecord,
    ItineraryRecord,
    ItinerarySegmentRecord,
    PriceSnapshotRecord,
    SearchEventRecord,
    SearchRecord,
    SupplierRecord,
)
from app.models import SearchRequest
from app.repositories import SearchPersistenceService, SearchRepository, sanitize_raw_payload
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator


def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def request() -> SearchRequest:
    return SearchRequest(
        originPlaceId="airport:MEL",
        destinationPlaceId="airport:PVG",
        departureDate=date(2026, 8, 12),
        minGapHours=3,
        maxGapHours=12,
        passengers=1,
        cabin="economy",
        candidateHubs=["BKK", "SIN"],
    )


def search_response():
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    return asyncio.run(service.search(request()))


def test_repository_persists_search_price_snapshots_itineraries_and_segments() -> None:
    factory = session_factory()
    response = search_response()
    session = factory()
    try:
        repo = SearchRepository(session)
        repo.save_search_result(request(), response)

        saved_search = session.get(SearchRecord, response.search_id)
        assert saved_search is not None
        assert saved_search.origin == "MEL"
        assert saved_search.destination == "PVG"

        snapshots = session.scalars(select(PriceSnapshotRecord)).all()
        assert snapshots
        assert all(snapshot.supplier for snapshot in snapshots)
        assert all(snapshot.expires_at for snapshot in snapshots)

        itineraries = session.scalars(select(ItineraryRecord)).all()
        assert len(itineraries) >= len(response.results.ranked_results)
        for itinerary in itineraries:
            segments = session.scalars(
                select(ItinerarySegmentRecord)
                .where(ItinerarySegmentRecord.itinerary_id == itinerary.id)
                .order_by(ItinerarySegmentRecord.sequence)
            ).all()
            assert segments
            assert [segment.sequence for segment in segments] == list(range(len(segments)))

        events = session.scalars(select(SearchEventRecord)).all()
        assert [event.event_type for event in events] == ["search.completed"]
    finally:
        session.close()


def test_search_service_persists_after_search_completion() -> None:
    factory = session_factory()
    service = SearchService(
        SearchOrchestrator(build_mock_orchestrator()),
        persistence_service=SearchPersistenceService(factory),
    )
    response = asyncio.run(service.search(request()))

    session = factory()
    try:
        assert session.get(SearchRecord, response.search_id) is not None
        assert session.scalars(select(ItineraryRecord)).first() is not None
        assert session.scalars(select(PriceSnapshotRecord)).first() is not None
    finally:
        session.close()


def test_repository_upserts_suppliers_and_airports() -> None:
    factory = session_factory()
    session = factory()
    try:
        repo = SearchRepository(session)
        repo.upsert_airport(
            iata_code="MEL",
            name="Melbourne Airport",
            city="Melbourne",
            country="Australia",
            timezone_name="Australia/Melbourne",
        )
        repo.save_search_result(request(), search_response())
        assert session.get(AirportRecord, "MEL") is not None
        assert {supplier.name for supplier in session.scalars(select(SupplierRecord)).all()}
    finally:
        session.close()


def test_raw_payload_is_sanitized_before_persistence() -> None:
    raw = {
        "fixture": "safe",
        "api_key": "secret",
        "nested": {"Authorization": "Bearer abc.xyz", "keep": "ok"},
        "cards": ["4111111111111111"],
    }
    sanitized = sanitize_raw_payload(raw)
    assert sanitized["fixture"] == "safe"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["Authorization"] == "[REDACTED]"
    assert sanitized["nested"]["keep"] == "ok"
    assert sanitized["cards"] == "[REDACTED]"
