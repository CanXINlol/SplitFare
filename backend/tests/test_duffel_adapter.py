from datetime import date

import pytest

from app.adapters.duffel import DuffelSupplierAdapter
from app.config import Settings
from app.models import Cabin, NormalizedFlightOffer, Supplier, VerificationStatus


class FakeResponse:
    def __init__(self, payload, status_error: Exception | None = None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append({
            "url": url,
            "headers": headers,
            "json": json,
            "timeout": timeout,
        })
        return FakeResponse(self.payload)


def duffel_payload():
    return {
        "data": {
            "offers": [{
                "id": "off_live_123",
                "total_amount": "998.50",
                "total_currency": "AUD",
                "expires_at": "2026-08-01T00:10:00Z",
                "slices": [{
                    "segments": [{
                        "id": "seg_live_1",
                        "origin": {"iata_code": "MEL"},
                        "destination": {"iata_code": "SIN"},
                        "departing_at": "2026-08-12T01:00:00Z",
                        "arriving_at": "2026-08-12T09:00:00Z",
                        "marketing_carrier": {"iata_code": "QF"},
                        "operating_carrier": {"iata_code": "QF"},
                        "marketing_carrier_flight_number": "35",
                    }, {
                        "id": "seg_live_2",
                        "origin": {"iata_code": "SIN"},
                        "destination": {"iata_code": "PVG"},
                        "departing_at": "2026-08-12T12:00:00Z",
                        "arriving_at": "2026-08-12T17:00:00Z",
                        "marketing_carrier": {"iata_code": "MU"},
                        "operating_carrier": {"iata_code": "MU"},
                        "marketing_carrier_flight_number": "568",
                    }]
                }]
            }]
        }
    }


def configured_adapter(http_client):
    return DuffelSupplierAdapter(
        Settings(
            duffel_api_token="duffel_test_token",
            duffel_base_url="https://api.duffel.test",
            external_api_timeout_seconds=7,
        ),
        http_client=http_client,
    )


def test_duffel_fetch_uses_backend_token_headers_payload_and_timeout() -> None:
    http_client = FakeHttpClient(duffel_payload())
    adapter = configured_adapter(http_client)

    raw = adapter._fetch_one_way("MEL", "PVG", date(2026, 8, 12), 2, Cabin.economy, "AUD")

    assert raw["data"]["offers"]
    call = http_client.calls[0]
    assert call["url"] == "https://api.duffel.test/air/offer_requests"
    assert call["headers"]["Authorization"] == "Bearer duffel_test_token"
    assert call["headers"]["Duffel-Version"] == "v2"
    assert call["timeout"] == 7
    assert call["json"]["data"]["slices"] == [{
        "origin": "MEL", "destination": "PVG", "departure_date": "2026-08-12",
    }]
    assert call["json"]["data"]["passengers"] == [{"type": "adult"}, {"type": "adult"}]
    assert call["json"]["data"]["return_offers"] is True


def test_duffel_response_normalizes_to_flight_offer_schema() -> None:
    adapter = configured_adapter(FakeHttpClient(duffel_payload()))
    raw = adapter._fetch_one_way("MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD")
    offers = adapter.normalize(raw)

    assert len(offers) == 1
    offer = offers[0]
    assert isinstance(offer, NormalizedFlightOffer)
    assert offer.supplier == Supplier.duffel
    assert offer.origin == "MEL"
    assert offer.destination == "PVG"
    assert offer.price_amount == 998.5
    assert offer.currency == "AUD"
    assert offer.protected_connection is True
    assert [segment.origin for segment in offer.segments] == ["MEL", "SIN"]
    assert [segment.destination for segment in offer.segments] == ["SIN", "PVG"]
    assert offer.raw_payload["id"] == "off_live_123"


def test_duffel_normalization_rejects_missing_price_currency_or_times() -> None:
    payload = duffel_payload()
    payload["data"]["offers"][0].pop("total_amount")
    adapter = configured_adapter(FakeHttpClient(payload))
    with pytest.raises(KeyError):
        adapter.normalize(payload)


def test_duffel_verify_price_is_safe_stub_not_confirmed() -> None:
    adapter = configured_adapter(FakeHttpClient(duffel_payload()))
    result = adapter.verify_price("off_live_123")
    assert result.status == VerificationStatus.unavailable
    assert result.is_confirmed is False
