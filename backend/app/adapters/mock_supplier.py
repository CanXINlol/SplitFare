from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.adapters.base import SupplierAdapter
from app.cache import CacheCategory, CachePolicy, MOCK_FLIGHT_PRICE_TTL_SECONDS
from app.data.mock_flights import MOCK_FLIGHTS
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceStatus,
    SearchRequest,
    Segment,
    Supplier,
    SupplierCapabilities,
    VerificationStatus,
    VerifyPriceResult,
)


class MockSupplierAdapter(SupplierAdapter):
    def __init__(self, supplier: Supplier = Supplier.mock_sky, scenario: str = "success"):
        if supplier not in {Supplier.mock_sky, Supplier.demo_air, Supplier.budget_demo}:
            raise ValueError("MockSupplierAdapter requires a mock supplier name.")
        self._name = supplier
        if scenario not in {"success", "timeout", "partial"}:
            raise ValueError("Unknown mock supplier scenario.")
        self.scenario = scenario

    @property
    def name(self) -> Supplier:
        return self._name

    @property
    def capabilities(self) -> SupplierCapabilities:
        return SupplierCapabilities(
            supports_search=True,
            supports_price_verify=True,
            supports_booking_url=False,
            supports_baggage_info=True,
            supports_split_ticket=True,
            supports_live_price=False,
        )

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
        if self.scenario == "timeout":
            raise TimeoutError("Deterministic mock supplier timeout.")
        flights = [
            flight for flight in MOCK_FLIGHTS
            if flight.supplier == self.name
            and flight.origin == origin
            and flight.destination == destination
        ]
        if self.scenario == "partial":
            flights = flights[:1]
        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
            "passengers": passengers,
            "cabin": cabin.value,
            "currency": currency,
            "flights": flights,
        }

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if not isinstance(raw_response, dict):
            raise ValueError("Mock response must be an object.")
        departure_date = date.fromisoformat(str(raw_response["departure_date"]))
        passengers = int(raw_response["passengers"])
        cabin = Cabin(str(raw_response["cabin"]))
        currency = str(raw_response["currency"])
        checked_at = datetime.now(timezone.utc)
        expires_at = checked_at + timedelta(seconds=MOCK_FLIGHT_PRICE_TTL_SECONDS)
        offers: list[NormalizedFlightOffer] = []
        for flight in raw_response["flights"]:
            departure = datetime.combine(
                departure_date,
                time(flight.departure_hour, flight.departure_minute),
                tzinfo=ZoneInfo(AIRPORT_TIME_ZONES.get(flight.origin, "UTC")),
            )
            arrival = (departure.astimezone(timezone.utc) + timedelta(minutes=flight.duration_minutes)).astimezone(
                ZoneInfo(AIRPORT_TIME_ZONES.get(flight.destination, "UTC"))
            )
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
                    id=(
                        f"offer-{flight.id}-{departure_date.isoformat()}-{passengers}p-"
                        f"{cabin.value}-{currency}"
                    ),
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

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        fixture_id, passengers, currency = parse_mock_offer_id(offer_id)
        flight = next(
            (item for item in MOCK_FLIGHTS if item.id == fixture_id and item.supplier == self.name),
            None,
        )
        checked_at = datetime.now(timezone.utc)
        available = flight is not None and flight.verification_available
        return VerifyPriceResult(
            offer_id=offer_id,
            supplier=self.name,
            status=VerificationStatus.verified if available else VerificationStatus.unavailable,
            price_status=PriceStatus.confirmed if available else PriceStatus.unavailable,
            price_amount=(flight.price + flight.verification_price_delta) * passengers if available else None,
            currency=currency if available else None,
            checked_at=checked_at,
            expires_at=checked_at + timedelta(seconds=MOCK_FLIGHT_PRICE_TTL_SECONDS) if available else None,
            message=(
                "Verified against deterministic mock data."
                if available
                else "This deterministic mock offer is unavailable."
                if flight
                else "Mock offer not found."
            ),
        )


AIRPORT_TIME_ZONES = {
    "MEL": "Australia/Melbourne",
    "PVG": "Asia/Shanghai",
    "SHA": "Asia/Shanghai",
    "BKK": "Asia/Bangkok",
    "SIN": "Asia/Singapore",
    "KUL": "Asia/Kuala_Lumpur",
    "HKG": "Asia/Hong_Kong",
    "TPE": "Asia/Taipei",
    "ICN": "Asia/Seoul",
    "NRT": "Asia/Tokyo",
    "CAN": "Asia/Shanghai",
}


def parse_mock_offer_id(offer_id: str) -> tuple[str, int, str]:
    value = offer_id.removeprefix("offer-")
    try:
        fixture_and_date, passenger_token, _cabin, currency = value.rsplit("-", 3)
        if not passenger_token.endswith("p"):
            raise ValueError
        fixture_id = fixture_and_date
        if len(fixture_and_date) > 11 and fixture_and_date[-11] == "-":
            try:
                date.fromisoformat(fixture_and_date[-10:])
                fixture_id = fixture_and_date[:-11]
            except ValueError:
                pass
        return fixture_id, int(passenger_token[:-1]), currency
    except (ValueError, TypeError):
        # Compatibility for direct contract checks created before the normalized ID format.
        return value, 1, "AUD"


class MockFlightSupplier:
    """Phase 0 compatibility facade. New code should use SupplierOrchestrator."""

    def search(self, request: SearchRequest) -> list[NormalizedFlightOffer]:
        from app.places import place_service

        origin = place_service.resolve(request.origin_place_id).airports[0].iata_code
        destination = place_service.resolve(request.destination_place_id).airports[0].iata_code
        offers: list[NormalizedFlightOffer] = []
        for supplier in (Supplier.mock_sky, Supplier.demo_air, Supplier.budget_demo):
            offers.extend(MockSupplierAdapter(supplier).search_one_way(
                origin,
                destination,
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
