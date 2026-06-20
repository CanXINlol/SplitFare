from datetime import datetime, time, timedelta, timezone

from app.adapters.base import FlightSupplier
from app.data.mock_flights import MOCK_FLIGHTS
from app.models import NormalizedFlightOffer, SearchRequest, Segment


class MockFlightSupplier(FlightSupplier):
    def search(self, request: SearchRequest) -> list[NormalizedFlightOffer]:
        checked_at = datetime.combine(request.departure_date, time(0), tzinfo=timezone.utc)
        expires_at = checked_at + timedelta(hours=2)
        offers: list[NormalizedFlightOffer] = []
        for flight in MOCK_FLIGHTS:
            departure = datetime.combine(
                request.departure_date,
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
                    price_amount=flight.price,
                    currency="AUD",
                    cabin=request.cabin,
                    baggage_included=flight.baggage_included,
                    booking_url=None,
                    raw_payload={"fixture": flight.id},
                    last_checked_at=checked_at,
                    expires_at=expires_at,
                    segments=[segment],
                    protected_connection=flight.protected_connection,
                )
            )
        return offers
