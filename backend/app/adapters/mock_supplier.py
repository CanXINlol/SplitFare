from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.adapters.base import SupplierAdapter
from app.cache import CacheCategory, CachePolicy, MOCK_FLIGHT_PRICE_TTL_SECONDS
from app.data.mock_flights import MOCK_FLIGHTS
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceVerification,
    SearchRequest,
    Segment,
    Supplier,
    VerificationStatus,
)


class MockSupplierAdapter(SupplierAdapter):
    def __init__(self, supplier: Supplier = Supplier.mock_sky):
        if supplier not in {Supplier.mock_sky, Supplier.demo_air, Supplier.budget_demo}:
            raise ValueError("MockSupplierAdapter requires a mock supplier name.")
        self._name = supplier

    @property
    def name(self) -> Supplier:
        return self._name

    @property
    def cache_policy(self) -> CachePolicy:
        return CachePolicy(CacheCategory.mock_flight_price, MOCK_FLIGHT_PRICE_TTL_SECONDS)

    def _fetch_one_way(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> Any:
        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
            "passengers": passengers,
            "cabin": cabin.value,
            "currency": currency,
            "flights": [
                flight for flight in MOCK_FLIGHTS
                if flight.supplier == self.name
                and flight.origin == origin
                and flight.destination == destination
            ],
        }

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if not isinstance(raw_response, dict):
            raise ValueError("Mock response must be an object.")
        departure_date = date.fromisoformat(str(raw_response["departure_date"]))
        passengers = int(raw_response["passengers"])
        cabin = Cabin(str(raw_response["cabin"]))
        currency = str(raw_response["currency"])
        checked_at = datetime.combine(departure_date, time(0), tzinfo=timezone.utc)
        expires_at = checked_at + timedelta(seconds=MOCK_FLIGHT_PRICE_TTL_SECONDS)
        offers: list[NormalizedFlightOffer] = []
        for flight in raw_response["flights"]:
            departure = datetime.combine(
                departure_date,
                time(flight.departure_hour, flight.departure_minute),
                tzinfo=timezone.utc,
            )
            arrival = departure + timedelta(minutes=flight.duration_minutes)
            segment = Segment(
                    id=flight.id,
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_at=departure,
                    arrival_at=arrival,
                    airline=flight.airline,
                    operating_airline=flight.airline,
                    flight_number=flight.flight_number,
            )
            offers.append(
                NormalizedFlightOffer(
                    id=f"offer-{flight.id}",
                    supplier=flight.supplier,
                    origin=flight.origin,
                    destination=flight.destination,
                    departure_at=departure,
                    arrival_at=arrival,
                    airline=flight.airline,
                    operating_airline=flight.airline,
                    flight_number=flight.flight_number,
                    price_amount=flight.price * passengers,
                    currency=currency,
                    cabin=cabin,
                    baggage_included=flight.baggage_included,
                    booking_url=None,
                    raw_payload={
                        "fixture": flight.id,
                        "adapter": self.name.value,
                        "requested_origin": raw_response.get("origin"),
                        "requested_destination": raw_response.get("destination"),
                    },
                    last_checked_at=checked_at,
                    expires_at=expires_at,
                    segments=[segment],
                    protected_connection=flight.protected_connection,
                )
            )
        return offers

    def verify_price(self, offer_id: str) -> PriceVerification:
        fixture_id = offer_id.removeprefix("offer-")
        flight = next(
            (item for item in MOCK_FLIGHTS if item.id == fixture_id and item.supplier == self.name),
            None,
        )
        checked_at = datetime.now(timezone.utc)
        return PriceVerification(
            offer_id=offer_id,
            supplier=self.name,
            status=VerificationStatus.verified if flight else VerificationStatus.unavailable,
            price_amount=flight.price if flight else None,
            currency="AUD" if flight else None,
            checked_at=checked_at,
            expires_at=checked_at + timedelta(seconds=MOCK_FLIGHT_PRICE_TTL_SECONDS) if flight else None,
            message="Verified against deterministic mock data." if flight else "Mock offer not found.",
        )


class MockFlightSupplier:
    """Phase 0 compatibility facade. New code should use SupplierOrchestrator."""

    def search(self, request: SearchRequest) -> list[NormalizedFlightOffer]:
        offers: list[NormalizedFlightOffer] = []
        for supplier in (Supplier.mock_sky, Supplier.demo_air, Supplier.budget_demo):
            offers.extend(MockSupplierAdapter(supplier).search_one_way(
                request.origin,
                request.destination,
                request.departure_date,
                request.passengers,
                request.cabin,
                request.currency,
            ))
        return offers


def build_mock_orchestrator():
    from app.adapters.orchestrator import SupplierOrchestrator

    return SupplierOrchestrator([
        MockSupplierAdapter(Supplier.mock_sky),
        MockSupplierAdapter(Supplier.demo_air),
        MockSupplierAdapter(Supplier.budget_demo),
    ])
