from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapter, SupplierAdapterError
from app.adapters.http_client import SupplierHttpClient
from app.cache import CacheCategory, CachePolicy
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


logger = logging.getLogger("splitfare.supplier.duffel")


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("missing supplier datetime")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("supplier datetime must contain a timezone")
    return parsed


def _airport_code(value: object) -> str:
    if isinstance(value, str):
        code = value
    elif isinstance(value, dict):
        code = str(value.get("iata_code") or "")
    else:
        code = ""
    code = code.upper()
    if len(code) != 3 or not code.isalpha():
        raise ValueError("supplier airport is missing an IATA code")
    return code


def _carrier(value: object) -> tuple[str, str | None]:
    if not isinstance(value, dict):
        raise ValueError("supplier carrier is missing")
    code = str(value.get("iata_code") or "").upper()
    if len(code) < 2:
        raise ValueError("supplier carrier is missing an IATA code")
    name = str(value.get("name") or "").strip() or None
    return code, name


def _extract_offers(raw_response: object) -> list[dict[str, Any]]:
    if not isinstance(raw_response, dict):
        raise SupplierAdapterError(
            "Duffel response must be an object.", code="SUPPLIER_INVALID_RESPONSE"
        )
    data = raw_response.get("data")
    if not isinstance(data, dict):
        raise SupplierAdapterError(
            "Duffel response is missing data.", code="SUPPLIER_INVALID_RESPONSE"
        )
    offers = data.get("offers")
    if isinstance(offers, list):
        return [offer for offer in offers if isinstance(offer, dict)]
    if data.get("id") and isinstance(data.get("slices"), list):
        return [data]
    raise SupplierAdapterError(
        "Duffel response is missing offers.", code="SUPPLIER_INVALID_RESPONSE"
    )


def _baggage_included(raw_segments: list[dict[str, Any]]) -> bool | None:
    baggage_fields_seen = False
    checked_bag = False
    for segment in raw_segments:
        for passenger in segment.get("passengers") or []:
            if not isinstance(passenger, dict) or "baggages" not in passenger:
                continue
            baggage_fields_seen = True
            for baggage in passenger.get("baggages") or []:
                if not isinstance(baggage, dict):
                    continue
                quantity = baggage.get("quantity", 0)
                if baggage.get("type") == "checked" and isinstance(quantity, int) and quantity > 0:
                    checked_bag = True
    return checked_bag if baggage_fields_seen else None


class DuffelSupplierAdapter(SupplierAdapter):
    """Authorised Duffel Flights API v2 adapter for disabled, test, and live modes."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: SupplierHttpClient | None = None,
    ):
        self.settings = settings or load_settings()
        self.http_client = http_client

    @property
    def name(self) -> Supplier:
        return Supplier.duffel

    @property
    def runtime_mode(self) -> str:
        return self.settings.duffel_mode

    @property
    def capabilities(self) -> SupplierCapabilities:
        requested = self.runtime_mode != "disabled"
        return SupplierCapabilities(
            supports_search=requested,
            supports_price_verify=requested,
            supports_booking_url=False,
            supports_baggage_info=requested,
            supports_split_ticket=requested,
            supports_live_price=self.runtime_mode == "live",
            supports_affiliate_link=False,
        )

    @property
    def cache_policy(self) -> CachePolicy:
        return CachePolicy(
            CacheCategory.live_flight_price,
            self.settings.duffel_cache_ttl_seconds,
            enabled=self.runtime_mode != "disabled",
            supplier_allows_cache=self.settings.duffel_allows_cache,
        )

    def _validate_configuration(self) -> str:
        if self.runtime_mode == "disabled":
            raise AdapterNotConfiguredError("Duffel supplier mode is disabled.")
        token = self.settings.duffel_api_token
        if not token:
            raise AdapterNotConfiguredError("Duffel access token is not configured.")
        is_test_token = token.startswith("duffel_test_")
        if self.runtime_mode == "sandbox" and not is_test_token:
            raise SupplierAdapterError(
                "Duffel sandbox mode requires a test access token.", code="SUPPLIER_AUTH_FAILED"
            )
        if self.runtime_mode == "live" and is_test_token:
            raise SupplierAdapterError(
                "Duffel live mode cannot use a test access token.", code="SUPPLIER_AUTH_FAILED"
            )
        return token

    def _client(self) -> SupplierHttpClient:
        token = self._validate_configuration()
        if self.http_client is not None:
            return self.http_client
        return SupplierHttpClient(
            base_url=self.settings.duffel_base_url,
            default_headers={
                "Authorization": f"Bearer {token}",
                "Duffel-Version": self.settings.duffel_api_version,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip",
            },
            timeout_seconds=self.settings.external_api_timeout_seconds,
            max_retries=self.settings.duffel_max_retries,
        )

    def _fetch_one_way(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        passengers: int,
        cabin: Cabin,
        currency: str,
    ) -> dict[str, Any]:
        correlation_id = str(uuid4())
        supplier_timeout_ms = max(
            2_000,
            min(60_000, int(max(2, self.settings.external_api_timeout_seconds - 1) * 1000)),
        )
        payload = {
            "data": {
                "slices": [{
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date.isoformat(),
                }],
                "passengers": [{"type": "adult"} for _ in range(passengers)],
                "cabin_class": cabin.value,
                # Each internal route leg must remain direct so SplitFare remains the
                # sole owner of the one-stop combination rule.
                "max_connections": 0,
            }
        }
        logger.info(
            "duffel.search_started correlation_id=%s mode=%s origin=%s destination=%s",
            correlation_id, self.runtime_mode, origin, destination,
        )
        raw = self._client().request(
            "POST",
            "/air/offer_requests",
            correlation_id=correlation_id,
            json=payload,
            params={"return_offers": "true", "supplier_timeout": supplier_timeout_ms},
        )
        raw["_splitfare"] = {
            "correlation_id": correlation_id,
            "mode": self.runtime_mode,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date.isoformat(),
            "passengers": passengers,
            "cabin": cabin.value,
            "requested_currency": currency,
        }
        return raw

    def _validate_response_mode(self, raw_response: dict[str, Any]) -> None:
        data = raw_response.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("live_mode"), bool):
            raise SupplierAdapterError(
                "Duffel response is missing live_mode.", code="SUPPLIER_INVALID_RESPONSE"
            )
        if self.runtime_mode == "sandbox" and data["live_mode"] is not False:
            raise SupplierAdapterError(
                "Duffel response mode did not match sandbox mode.", code="SUPPLIER_INVALID_RESPONSE"
            )
        if self.runtime_mode == "live" and data["live_mode"] is not True:
            raise SupplierAdapterError(
                "Duffel response mode did not match live mode.", code="SUPPLIER_INVALID_RESPONSE"
            )

    def normalize(self, raw_response: Any) -> list[NormalizedFlightOffer]:
        if raw_response in (None, [], {}):
            return []
        if not isinstance(raw_response, dict):
            raise SupplierAdapterError(
                "Duffel response must be an object.", code="SUPPLIER_INVALID_RESPONSE"
            )
        self._validate_response_mode(raw_response)
        context = raw_response.get("_splitfare") if isinstance(raw_response.get("_splitfare"), dict) else {}
        try:
            cabin = Cabin(str(context.get("cabin", Cabin.economy.value)))
        except ValueError as exception:
            raise SupplierAdapterError(
                "Duffel request context has an invalid cabin.", code="SUPPLIER_INVALID_RESPONSE"
            ) from exception
        checked_at = datetime.now(timezone.utc)
        normalized: list[NormalizedFlightOffer] = []
        for offer in _extract_offers(raw_response):
            try:
                raw_segments = [
                    segment
                    for flight_slice in offer["slices"]
                    if isinstance(flight_slice, dict)
                    for segment in flight_slice.get("segments", [])
                    if isinstance(segment, dict)
                ]
                if not raw_segments:
                    raise ValueError("offer has no segments")
                segments: list[Segment] = []
                for index, raw_segment in enumerate(raw_segments):
                    marketing_code, marketing_name = _carrier(raw_segment.get("marketing_carrier"))
                    operating_code, operating_name = _carrier(
                        raw_segment.get("operating_carrier") or raw_segment.get("marketing_carrier")
                    )
                    flight_suffix = str(raw_segment.get("marketing_carrier_flight_number") or "").strip()
                    if not flight_suffix:
                        raise ValueError("segment has no flight number")
                    segments.append(Segment(
                        id=str(raw_segment.get("id") or f"{offer['id']}-segment-{index}"),
                        origin=_airport_code(raw_segment.get("origin")),
                        destination=_airport_code(raw_segment.get("destination")),
                        departure_at=_parse_datetime(raw_segment.get("departing_at")),
                        arrival_at=_parse_datetime(raw_segment.get("arriving_at")),
                        airline=marketing_code,
                        operating_airline=operating_code,
                        marketing_airline_name=marketing_name,
                        operating_airline_name=operating_name,
                        flight_number=f"{marketing_code}{flight_suffix}",
                    ))
                price = Decimal(str(offer["total_amount"]))
                currency = str(offer["total_currency"]).upper()
                expires_at = _parse_datetime(offer.get("expires_at"))
                if expires_at <= checked_at:
                    raise ValueError("offer is already expired")
                raw_payload = dict(offer)
                raw_payload["_splitfare"] = {
                    "correlation_id": context.get("correlation_id"),
                    "mode": self.runtime_mode,
                }
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
                    price_amount=price,
                    currency=currency,
                    price_status=PriceStatus.confirmed,
                    cabin=cabin,
                    baggage_included=_baggage_included(raw_segments),
                    booking_url=None,
                    booking_reference=str(offer["id"]),
                    raw_payload=raw_payload,
                    last_checked_at=checked_at,
                    expires_at=expires_at,
                    segments=segments,
                    protected_connection=True,
                ))
            except (KeyError, TypeError, ValueError, InvalidOperation, ValidationError) as exception:
                logger.warning(
                    "duffel.offer_filtered offer_id=%s reason=%s",
                    offer.get("id", "unknown"), type(exception).__name__,
                )
        return normalized

    def verify_price_result(self, offer_id: str) -> VerifyPriceResult:
        checked_at = datetime.now(timezone.utc)
        try:
            correlation_id = str(uuid4())
            raw = self._client().request(
                "GET",
                f"/air/offers/{offer_id}",
                correlation_id=correlation_id,
                params={"return_available_services": "true"},
            )
            raw["_splitfare"] = {
                "correlation_id": correlation_id,
                "mode": self.runtime_mode,
                "cabin": Cabin.economy.value,
            }
            offers = self.normalize(raw)
        except AdapterNotConfiguredError:
            return VerifyPriceResult(
                offer_id=offer_id, supplier=self.name, status=VerificationStatus.unsupported,
                price_status=PriceStatus.unavailable, supported=False, checked_at=checked_at,
                message="SUPPLIER_VERIFY_UNSUPPORTED",
            )
        except SupplierAdapterError as exception:
            if exception.status_code in {404, 410, 422}:
                return VerifyPriceResult(
                    offer_id=offer_id, supplier=self.name, status=VerificationStatus.unavailable,
                    price_status=PriceStatus.unavailable, supported=True, checked_at=checked_at,
                    message="SUPPLIER_OFFER_UNAVAILABLE",
                )
            raise
        if not offers:
            return VerifyPriceResult(
                offer_id=offer_id, supplier=self.name, status=VerificationStatus.unavailable,
                price_status=PriceStatus.unavailable, supported=True, checked_at=checked_at,
                message="SUPPLIER_OFFER_INVALID",
            )
        offer = offers[0]
        return VerifyPriceResult(
            offer_id=offer.id,
            supplier=self.name,
            status=VerificationStatus.verified,
            price_status=PriceStatus.confirmed,
            price_amount=offer.price_amount,
            currency=offer.currency,
            checked_at=offer.last_checked_at,
            expires_at=offer.expires_at,
            supported=True,
            booking_url=None,
            message="SUPPLIER_PRICE_VERIFIED",
        )
