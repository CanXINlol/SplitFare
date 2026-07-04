from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

import httpx

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapter
from app.cache import LIVE_FLIGHT_PRICE_TTL_SECONDS
from app.config import Settings, load_settings
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    PriceStatus,
    Segment,
    Supplier,
    SupplierCapabilities,
    VerificationStatus,
    VerifyPriceResult,
)


class HttpClient(Protocol):
    def post(self, url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: float) -> Any:
        ...


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _carrier_code(value: dict[str, Any] | None) -> str:
    if not value:
        return "XX"
    return str(value.get("iata_code") or value.get("iataCode") or value.get("id") or "XX")


def _airport_code(value: dict[str, Any] | str) -> str:
    if isinstance(value, str):
        return value
    return str(value.get("iata_code") or value.get("iataCode") or value.get("id") or "")


def _extract_offers(raw_response: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_response, dict):
        raise ValueError("Duffel response must be an object.")
    data = raw_response.get("data", raw_response)
    if isinstance(data, dict) and isinstance(data.get("offers"), list):
        return data["offers"]
    if isinstance(data, list):
        return data
    return []


class DuffelSupplierAdapter(SupplierAdapter):
    def __init__(
        self,
        settings: Settings | None = None,
        http_client: HttpClient | None = None,
    ):
        self.settings = settings or load_settings()
        self.http_client = http_client or httpx

    @property
    def name(self) -> Supplier:
        return Supplier.duffel

    @property
    def capabilities(self) -> SupplierCapabilities:
        configured = bool(self.settings.duffel_api_token)
        return SupplierCapabilities(
            supports_search=configured,
            supports_price_verify=False,
            supports_booking_url=False,
            supports_baggage_info=False,
            supports_split_ticket=False,
            supports_live_price=configured,
            supports_affiliate_link=False,
        )

    def _fetch_one_way(
        self, origin: str, destination: str, departure_date: date,
        passengers: int, cabin: Cabin, currency: str,
    ) -> Any:
        if not self.settings.duffel_api_token:
            raise AdapterNotConfiguredError("Duffel adapter is disabled because DUFFEL_API_TOKEN is not set.")
        payload = {
            "data": {
                "slices": [{
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date.isoformat(),
                }],
                "passengers": [{"type": "adult"} for _ in range(passengers)],
                "cabin_class": cabin.value,
                "return_offers": True,
            }
        }
        response = self.http_client.post(
            f"{self.settings.duffel_base_url}/air/offer_requests",
            headers={
                "Authorization": f"Bearer {self.settings.duffel_api_token}",
                "Duffel-Version": self.settings.duffel_api_version,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=self.settings.external_api_timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        if isinstance(raw, dict):
            raw.setdefault("_splitfare_request", {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date.isoformat(),
                "passengers": passengers,
                "cabin": cabin.value,
                "currency": currency,
            })
        return raw

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if raw_response in (None, [], {}):
            return []
        request_context = raw_response.get("_splitfare_request", {}) if isinstance(raw_response, dict) else {}
        cabin = Cabin(str(request_context.get("cabin", Cabin.economy.value)))
        checked_at = datetime.now(timezone.utc)
        normalized: list[NormalizedFlightOffer] = []
        for offer in _extract_offers(raw_response):
            slices = offer.get("slices") or []
            if not slices:
                continue
            raw_segments = [
                segment
                for flight_slice in slices
                for segment in flight_slice.get("segments", [])
            ]
            if not raw_segments:
                continue
            segments: list[Segment] = []
            for index, segment in enumerate(raw_segments):
                marketing_carrier = segment.get("marketing_carrier") or segment.get("marketingCarrier")
                operating_carrier = (
                    segment.get("operating_carrier")
                    or segment.get("operatingCarrier")
                    or marketing_carrier
                )
                airline = _carrier_code(marketing_carrier)
                operating_airline = _carrier_code(operating_carrier)
                flight_number_suffix = str(
                    segment.get("marketing_carrier_flight_number")
                    or segment.get("marketingCarrierFlightNumber")
                    or segment.get("flight_number")
                    or segment.get("flightNumber")
                    or "000"
                )
                departure_at = _parse_datetime(str(segment["departing_at"]))
                arrival_at = _parse_datetime(str(segment["arriving_at"]))
                segments.append(Segment(
                    id=str(segment.get("id") or f"{offer['id']}-segment-{index}"),
                    origin=_airport_code(segment["origin"]),
                    destination=_airport_code(segment["destination"]),
                    departure_at=departure_at,
                    arrival_at=arrival_at,
                    airline=airline,
                    operating_airline=operating_airline,
                    flight_number=f"{airline}{flight_number_suffix}",
                ))
            expires_at = (
                _parse_datetime(str(offer["expires_at"]))
                if offer.get("expires_at")
                else checked_at + timedelta(seconds=LIVE_FLIGHT_PRICE_TTL_SECONDS)
            )
            normalized.append(NormalizedFlightOffer(
                id=str(offer["id"]),
                supplier=self.name,
                origin=segments[0].origin,
                destination=segments[-1].destination,
                departure_at=segments[0].departure_at,
                arrival_at=segments[-1].arrival_at,
                airline=segments[0].airline,
                operating_airline=segments[0].operating_airline,
                flight_number=segments[0].flight_number,
                price_amount=float(offer["total_amount"]),
                currency=str(offer["total_currency"]),
                cabin=cabin,
                baggage_included=None,
                booking_url=None,
                raw_payload=offer,
                last_checked_at=checked_at,
                expires_at=expires_at,
                segments=segments,
                protected_connection=True,
            ))
        return normalized

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        if not self.settings.duffel_api_token:
            return VerifyPriceResult(
                offer_id=offer_id, supplier=self.name, status=VerificationStatus.unsupported,
                price_status=PriceStatus.unavailable,
                supported=False,
                checked_at=datetime.now(timezone.utc),
                message="Duffel price verification is not configured because DUFFEL_API_TOKEN is not set.",
            )
        return VerifyPriceResult(
            offer_id=offer_id, supplier=self.name, status=VerificationStatus.unsupported,
            price_status=PriceStatus.unavailable,
            supported=False,
            checked_at=datetime.now(timezone.utc),
            message="Duffel adapter is configured, but live price verification is a safe stub in Phase 8.",
        )
