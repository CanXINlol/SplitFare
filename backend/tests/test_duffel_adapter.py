import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from app.adapters.base import AdapterNotConfiguredError, SupplierAdapterError
from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.http_client import SupplierHttpClient
from app.config import Settings
from app.models import Cabin, PriceStatus, Supplier, VerificationStatus


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "duffel_offer_request_sandbox.json").read_text(encoding="utf-8")
)


def settings(**updates) -> Settings:
    values = {
        "enable_mock_supplier": False,
        "duffel_mode": "sandbox",
        "duffel_api_token": "duffel_test_authorised_fixture",
        "duffel_base_url": "https://api.duffel.com",
        "external_api_timeout_seconds": 7,
        "duffel_max_retries": 1,
    }
    values.update(updates)
    return Settings(**values)


def client(handler, *, retries: int = 1, sleep=lambda _: None) -> SupplierHttpClient:
    return SupplierHttpClient(
        base_url="https://api.duffel.com",
        default_headers={
            "Authorization": "Bearer duffel_test_authorised_fixture",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout_seconds=7,
        max_retries=retries,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleep,
    )


def test_search_uses_official_endpoint_headers_query_and_airport_payload() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        seen["payload"] = json.loads(request.content)
        return httpx.Response(201, json=FIXTURE)

    adapter = DuffelSupplierAdapter(settings(), client(handler))
    offers = adapter.search_one_way("MEL", "PVG", date(2026, 8, 12), 2, Cabin.economy, "AUD")
    request = seen["request"]
    assert request.method == "POST"
    assert request.url.path == "/air/offer_requests"
    assert request.url.params["return_offers"] == "true"
    assert request.url.params["supplier_timeout"] == "6000"
    assert request.headers["Authorization"] == "Bearer duffel_test_authorised_fixture"
    assert request.headers["Duffel-Version"] == "v2"
    assert seen["payload"]["data"]["slices"] == [{
        "origin": "MEL", "destination": "PVG", "departure_date": "2026-08-12"
    }]
    assert seen["payload"]["data"]["passengers"] == [{"type": "adult"}, {"type": "adult"}]
    assert seen["payload"]["data"]["max_connections"] == 0
    assert len(offers) == 1


def test_sandbox_response_normalizes_complete_offer() -> None:
    adapter = DuffelSupplierAdapter(settings())
    payload = json.loads(json.dumps(FIXTURE))
    payload["_splitfare"] = {"mode": "sandbox", "cabin": "economy", "correlation_id": "internal-1"}
    offer = adapter.normalize(payload)[0]
    assert offer.supplier == Supplier.duffel
    assert offer.id == "off_sandbox_123"
    assert offer.booking_reference == "off_sandbox_123"
    assert offer.origin == "MEL" and offer.destination == "PVG"
    assert offer.price_amount == Decimal("998.50")
    assert offer.currency == "AUD"
    assert offer.price_status == PriceStatus.confirmed
    assert offer.baggage_included is True
    assert offer.segments[0].operating_airline_name == "Qantas"
    assert offer.raw_payload["_splitfare"]["mode"] == "sandbox"


@pytest.mark.parametrize("missing", ["total_amount", "total_currency", "expires_at"])
def test_incomplete_offer_is_filtered_not_confirmed(missing: str) -> None:
    payload = json.loads(json.dumps(FIXTURE))
    payload["data"]["offers"][0].pop(missing)
    adapter = DuffelSupplierAdapter(settings())
    assert adapter.normalize(payload) == []


def test_offer_with_naive_time_is_filtered() -> None:
    payload = json.loads(json.dumps(FIXTURE))
    payload["data"]["offers"][0]["slices"][0]["segments"][0]["departing_at"] = "2026-08-12T01:00:00"
    assert DuffelSupplierAdapter(settings()).normalize(payload) == []


def test_response_mode_mismatch_is_rejected() -> None:
    payload = json.loads(json.dumps(FIXTURE))
    payload["data"]["live_mode"] = True
    with pytest.raises(SupplierAdapterError) as captured:
        DuffelSupplierAdapter(settings()).normalize(payload)
    assert captured.value.code == "SUPPLIER_INVALID_RESPONSE"


def test_timeout_maps_to_stable_code_without_unbounded_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow", request=request)

    adapter = DuffelSupplierAdapter(settings(), client(handler, retries=2))
    with pytest.raises(SupplierAdapterError) as captured:
        adapter.search_one_way("MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD")
    assert captured.value.code == "SUPPLIER_TIMEOUT"
    assert calls == 1


def test_rate_limit_is_retried_once_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"ratelimit-reset": "0"}, json={
                "errors": [{"code": "rate_limit_exceeded"}],
                "meta": {"request_id": "req_rate", "status": 429},
            })
        return httpx.Response(201, json=FIXTURE)

    offers = DuffelSupplierAdapter(settings(), client(handler)).search_one_way(
        "MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD"
    )
    assert offers and calls == 2


def test_rate_limit_exhaustion_maps_to_stable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"meta": {"request_id": "req_rate", "status": 429}})

    adapter = DuffelSupplierAdapter(settings(), client(handler, retries=0))
    with pytest.raises(SupplierAdapterError) as captured:
        adapter.search_one_way("MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD")
    assert captured.value.code == "SUPPLIER_RATE_LIMITED"
    assert captured.value.request_id == "req_rate"


def test_authentication_error_maps_to_stable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"meta": {"request_id": "req_auth", "status": 401}})

    with pytest.raises(SupplierAdapterError) as captured:
        DuffelSupplierAdapter(settings(), client(handler)).search_one_way(
            "MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD"
        )
    assert captured.value.code == "SUPPLIER_AUTH_FAILED"


def test_missing_token_does_not_break_startup_but_search_is_not_configured() -> None:
    adapter = DuffelSupplierAdapter(settings(duffel_api_token=None))
    assert adapter.capabilities.supports_search is True
    with pytest.raises(AdapterNotConfiguredError):
        adapter.search_one_way("MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD")


def test_disabled_mode_has_no_search_or_verify_capability() -> None:
    adapter = DuffelSupplierAdapter(settings(duffel_mode="disabled", duffel_api_token=None))
    assert adapter.capabilities.supports_search is False
    assert adapter.capabilities.supports_price_verify is False
    assert adapter.verify_price("off_disabled").status == VerificationStatus.unsupported


def test_verify_price_gets_current_offer_and_returns_confirmed_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/air/offers/off_sandbox_123"
        payload = {"data": {**FIXTURE["data"]["offers"][0], "live_mode": False}}
        return httpx.Response(200, json=payload)

    result = DuffelSupplierAdapter(settings(), client(handler)).verify_price("off_sandbox_123")
    assert result.status == VerificationStatus.verified
    assert result.price_status == PriceStatus.confirmed
    assert result.price_amount == Decimal("998.50")
    assert result.is_confirmed is True


def test_verify_price_returns_unavailable_for_missing_offer() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"meta": {"request_id": "req_missing", "status": 404}})

    result = DuffelSupplierAdapter(settings(), client(handler, retries=0)).verify_price("off_missing")
    assert result.status == VerificationStatus.unavailable
    assert result.price_status == PriceStatus.unavailable
    assert result.is_confirmed is False


def test_cache_policy_is_explicit_and_configurable() -> None:
    adapter = DuffelSupplierAdapter(settings(duffel_cache_ttl_seconds=321, duffel_allows_cache=True))
    assert adapter.cache_policy.ttl_seconds == 321
    assert adapter.cache_policy.can_store is True
