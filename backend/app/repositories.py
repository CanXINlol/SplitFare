from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import (
    AirportRecord,
    ItineraryRecord,
    ItinerarySegmentRecord,
    PriceSnapshotRecord,
    SearchEventRecord,
    SearchRecord,
    SupplierRecord,
)
from app.models import (
    Itinerary,
    NormalizedFlightOffer,
    SearchRequest,
    SearchResponse,
    Supplier,
    VerificationStatus,
)


SENSITIVE_RAW_KEYS = re.compile(r"(?i)(token|api[_-]?key|authorization|secret|password|card|passport)")


def sanitize_raw_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_RAW_KEYS.search(str(key)):
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = sanitize_raw_payload(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_raw_payload(item) for item in value]
    if isinstance(value, str) and re.search(r"(?i)\bbearer\s+[A-Za-z0-9._~+\-/]+=*", value):
        return "Bearer [REDACTED]"
    return value


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stored_route_code(place_id: str, response: SearchResponse, side: str) -> str:
    if response.ranked_results:
        segment = response.ranked_results[0].segments[0 if side == "origin" else -1]
        return segment.origin if side == "origin" else segment.destination
    if place_id.lower().startswith("airport:"):
        return place_id.split(":", 1)[1].upper()
    return "LOC"


def _supplier_cache_policy(supplier: Supplier) -> dict[str, Any]:
    from app.cache import default_supplier_cache_policy

    policy = default_supplier_cache_policy(supplier)
    return {
        "category": policy.category.value,
        "ttl_seconds": policy.ttl_seconds,
        "enabled": policy.enabled,
        "supplier_allows_cache": policy.supplier_allows_cache,
    }


class SearchRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_airport(
        self,
        *,
        iata_code: str,
        name: str,
        city: str,
        country: str,
        timezone_name: str,
    ) -> AirportRecord:
        airport = self.session.get(AirportRecord, iata_code)
        if airport is None:
            airport = AirportRecord(
                iata_code=iata_code,
                name=name,
                city=city,
                country=country,
                timezone=timezone_name,
            )
            self.session.add(airport)
        else:
            airport.name = name
            airport.city = city
            airport.country = country
            airport.timezone = timezone_name
        return airport

    def upsert_supplier(self, supplier: Supplier) -> SupplierRecord:
        existing = self.session.get(SupplierRecord, supplier.value)
        cache_policy = _supplier_cache_policy(supplier)
        if existing is not None:
            existing.cache_policy = cache_policy
            existing.allows_cache = bool(cache_policy["supplier_allows_cache"])
            return existing
        record = SupplierRecord(
            name=supplier.value,
            display_name=supplier.value,
            cache_policy=cache_policy,
            allows_cache=bool(cache_policy["supplier_allows_cache"]),
        )
        self.session.add(record)
        return record

    def save_search_result(self, request: SearchRequest, response: SearchResponse) -> SearchRecord:
        for supplier in Supplier:
            self.upsert_supplier(supplier)

        search = SearchRecord(
            id=response.search_id,
            origin=_stored_route_code(request.origin_place_id, response, "origin"),
            destination=_stored_route_code(request.destination_place_id, response, "destination"),
            departure_date=request.departure_date,
            min_gap_minutes=round(request.min_gap_hours * 60),
            max_gap_minutes=round(request.max_gap_hours * 60),
            passengers=request.passengers,
            cabin=request.cabin.value,
            currency=request.currency,
            sort=request.sort.value,
            status=response.status.value,
            candidate_hubs=request.candidate_hubs,
            errors=[error.model_dump(mode="json") for error in response.errors],
            explanation=response.explanation,
        )
        self.session.merge(search)

        offers = self._unique_returned_offers(response)
        for offer in offers:
            self.session.merge(self._price_snapshot_record(request, response.search_id, offer))

        ranked_ids = {itinerary.id: index + 1 for index, itinerary in enumerate(response.ranked_results)}
        for itinerary in self._unique_itineraries(response):
            db_itinerary_id = self._db_itinerary_id(response.search_id, itinerary.id)
            self.session.merge(
                self._itinerary_record(
                    response.search_id, itinerary, ranked_ids.get(itinerary.id), db_itinerary_id
                )
            )
            for sequence, segment in enumerate(itinerary.segments):
                offer = self._offer_for_segment(itinerary, segment.id)
                self.session.add(ItinerarySegmentRecord(
                    itinerary_id=db_itinerary_id,
                    search_id=response.search_id,
                    offer_id=offer.id if offer else None,
                    segment_id=segment.id,
                    sequence=sequence,
                    origin=segment.origin,
                    destination=segment.destination,
                    departure_at=segment.departure_at,
                    arrival_at=segment.arrival_at,
                    airline=segment.airline,
                    operating_airline=segment.operating_airline,
                    flight_number=segment.flight_number,
                    supplier=offer.supplier.value if offer else "unknown",
                ))

        self.session.add(SearchEventRecord(
            search_id=response.search_id,
            event_type="search.completed",
            payload={
                "status": response.status.value,
                "ranked_count": len(response.ranked_results),
                "protected_count": len(response.protected_itineraries),
                "split_ticket_count": len(response.split_ticket_itineraries),
            },
        ))
        self.session.commit()
        return self.session.get(SearchRecord, response.search_id) or search

    def get_search(self, search_id: str) -> SearchRecord | None:
        return self.session.get(SearchRecord, search_id)

    def count_itinerary_segments(self, itinerary_id: str) -> int:
        return len(self.session.scalars(
            select(ItinerarySegmentRecord).where(ItinerarySegmentRecord.itinerary_id == itinerary_id)
        ).all())

    def record_search_event(
        self, search_id: str, event_type: str, payload: dict[str, Any]
    ) -> SearchEventRecord:
        event = SearchEventRecord(
            search_id=search_id,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(event)
        self.session.commit()
        return event

    def _price_snapshot_record(
        self, request: SearchRequest, search_id: str, offer: NormalizedFlightOffer
    ) -> PriceSnapshotRecord:
        created_at = _now()
        return PriceSnapshotRecord(
            id=f"{search_id}:{offer.supplier.value}:{offer.id}",
            search_id=search_id,
            offer_id=offer.id,
            supplier=offer.supplier.value,
            origin=offer.origin,
            destination=offer.destination,
            departure_at=offer.departure_at,
            arrival_at=offer.arrival_at,
            departure_date=request.departure_date,
            passengers=request.passengers,
            cabin=offer.cabin.value,
            price_amount=offer.price_amount,
            currency=offer.currency,
            baggage_included=offer.baggage_included,
            booking_url=str(offer.booking_url) if offer.booking_url else None,
            raw_payload=sanitize_raw_payload(offer.raw_payload),
            last_checked_at=offer.last_checked_at,
            expires_at=offer.expires_at,
            verification_status=(
                VerificationStatus.verified.value
                if offer.expires_at > created_at
                else VerificationStatus.expired.value
            ),
            created_at=created_at,
        )

    def _itinerary_record(
        self, search_id: str, itinerary: Itinerary, rank: int | None, db_itinerary_id: str
    ) -> ItineraryRecord:
        return ItineraryRecord(
            id=db_itinerary_id,
            search_id=search_id,
            type=itinerary.type.value,
            total_price=itinerary.total_price,
            currency=itinerary.currency,
            total_duration_minutes=itinerary.total_duration_minutes,
            layover_airport=itinerary.layover_airport,
            layover_departure_airport=itinerary.layover_departure_airport,
            layover_gap_minutes=itinerary.layover_gap_minutes,
            requires_ground_transfer=itinerary.requires_ground_transfer,
            risk_score=itinerary.risk_score,
            risk_level=itinerary.risk_level.value,
            savings_vs_baseline=itinerary.savings_vs_baseline,
            value_score=itinerary.value_score,
            warnings=itinerary.warnings,
            suppliers=[supplier.value for supplier in itinerary.suppliers],
            offer_ids=[offer.id for offer in itinerary.offers],
            last_checked_at=itinerary.last_checked_at,
            expires_at=itinerary.expires_at,
            rank=rank,
        )

    def _db_itinerary_id(self, search_id: str, itinerary_id: str) -> str:
        return f"{search_id}:{itinerary_id}"

    def _unique_itineraries(self, response: SearchResponse) -> list[Itinerary]:
        unique: dict[str, Itinerary] = {}
        for itinerary in (
            response.protected_itineraries
            + response.split_ticket_itineraries
            + response.ranked_results
        ):
            unique.setdefault(itinerary.id, itinerary)
        return list(unique.values())

    def _unique_returned_offers(self, response: SearchResponse) -> list[NormalizedFlightOffer]:
        unique: dict[tuple[str, str], NormalizedFlightOffer] = {}
        for itinerary in self._unique_itineraries(response):
            for offer in itinerary.offers:
                unique.setdefault((offer.supplier.value, offer.id), offer)
        return list(unique.values())

    def _offer_for_segment(
        self, itinerary: Itinerary, segment_id: str
    ) -> NormalizedFlightOffer | None:
        return next(
            (
                offer
                for offer in itinerary.offers
                if any(segment.id == segment_id for segment in offer.segments)
            ),
            None,
        )


class SearchPersistenceService:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def persist_search(self, request: SearchRequest, response: SearchResponse) -> None:
        session = self.session_factory()
        try:
            SearchRepository(session).save_search_result(request, response)
        finally:
            session.close()

    def record_event(self, search_id: str, event_type: str, payload: dict[str, Any]) -> None:
        session = self.session_factory()
        try:
            SearchRepository(session).record_search_event(search_id, event_type, payload)
        finally:
            session.close()
