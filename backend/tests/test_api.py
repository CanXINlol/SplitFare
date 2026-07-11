from dataclasses import replace
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

import app.main as main_module
from app.config import Settings
from app.db import SessionLocal
from app.db_models import SearchEventRecord
from app.main import app, build_supplier_adapters
from app.models import (
    BookingOption,
    BookingOptionType,
    PriceStatus,
    Supplier,
    SupplierCapabilities,
    VerificationStatus,
    VerifyPriceResult,
)


client = TestClient(app)


@app.get("/_test-error")
def _test_error() -> None:
    raise RuntimeError("raw secret stack detail")


def test_health_endpoint_exposes_deployment_shape() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["mode"] in {"mock", "live"}
    assert body["timestamp"]


def test_city_catalog_api_exposes_the_authoritative_hierarchy() -> None:
    response = client.get("/api/cities")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "city-catalog-v1"
    assert {item["continentId"] for item in body["continents"]} == {
        "asia", "oceania", "europe", "north-america"
    }
    assert any(city["cityId"] == "city:melbourne-au" for city in body["cities"])
    assert any(city["cityId"] == "city:shanghai-cn" for city in body["cities"])


def test_old_place_endpoints_are_removed() -> None:
    assert client.get("/api/places/search", params={"q": "Melbourne"}).status_code == 404
    assert client.post("/api/places/resolve", json={"placeId": "airport:PVG"}).status_code == 404


def test_invalid_city_id_returns_stable_validation_error() -> None:
    response = client.post("/api/search", json={
        "originCityId": "city:missing", "destinationCityId": "city:shanghai-cn",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy",
    })
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "invalid_city_id"


def test_rate_limit_applies_to_search_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, rate_limit_requests_per_minute=1),
    )
    main_module._rate_limit_hits.clear()
    payload = {
        "originCityId": "city:sydney-au", "destinationCityId": "city:london-gb",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy", "candidateHubs": [],
    }
    assert client.post("/api/search", json=payload).status_code == 200
    limited = client.post("/api/search", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    main_module._rate_limit_hits.clear()


def test_production_error_response_hides_raw_exception(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, app_env="production"))
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/_test-error")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Internal server error."
    assert "raw secret stack detail" not in str(body)


def test_search_api_uses_camel_case_contract() -> None:
    response = client.post("/api/search", json={
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["searchId"]
    assert body["status"] == "complete"
    assert body["results"]["rankedResults"]
    assert body["errors"] == []
    assert body["baseline"]["totalPrice"] > 0
    assert body["cheapestSplit"]["type"] == "split_ticket"
    offer = body["cheapestSplit"]["offers"][0]
    assert set({
        "id", "supplier", "origin", "destination", "departureAt", "arrivalAt",
        "airline", "operatingAirline", "flightNumber", "priceAmount", "currency",
        "cabin", "baggageIncluded", "bookingUrl", "lastCheckedAt", "expiresAt",
    }).issubset(offer)
    assert "rawPayload" not in offer
    assert body["cheapestSplit"]["riskAssessment"]["score"] == body["cheapestSplit"]["riskScore"]
    assert body["cheapestSplit"]["priceFreshness"]["lastCheckedAt"] == body["cheapestSplit"]["lastCheckedAt"]
    assert body["cheapestSplit"]["priceFreshness"]["expiresAt"] == body["cheapestSplit"]["expiresAt"]
    assert body["cheapestSplit"]["priceFreshness"]["isExpired"] is False
    options = body["cheapestSplit"]["bookingOptions"]
    assert options
    assert all(option["bookingOptionId"] == option["id"] for option in options)
    assert all(option["supportsPriceVerify"] is True for option in options)
    assert all(option["supplier"] not in {"TripComAffiliate", "Skyscanner"} for option in options)
    assert body["metadata"]["demoData"] is True
    assert body["metadata"]["mode"] == "mock"
    assert body["metadata"]["supplierQueryCount"] <= body["metadata"]["supplierQueryLimit"]
    assert body["cheapestSplit"]["priceSourceCoverage"]["confirmedSupplierCount"] >= 1
    assert body["results"]["baselinePrice"] == body["baseline"]["totalPrice"]
    assert body["results"]["protectedItineraries"]
    assert body["results"]["splitTicketItineraries"]
    assert len(body["results"]["rankedResults"]) <= 20
    assert "rankedResults" not in body
    assert body["supplierFailures"] == []


def test_openapi_contract_uses_location_search_and_canonical_verification_fields() -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    search_properties = schemas["SearchRequest"]["properties"]
    assert "originCityId" in search_properties
    assert "destinationCityId" in search_properties
    assert "origin" not in search_properties
    assert "destination" not in search_properties
    response_required = set(schemas["SearchResponse"]["required"])
    assert {"searchId", "status", "results", "metadata", "disclaimer"} <= response_required
    verification_properties = set(schemas["PreBookingVerificationRequest"]["properties"])
    assert verification_properties == {"searchId", "itineraryId", "bookingOptionId"}


def test_raw_payload_requires_explicit_debug_flag() -> None:
    payload = {
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    }
    regular = client.post("/api/search", json=payload).json()
    debug = client.post("/api/search?debug=true", json=payload).json()
    assert "rawPayload" not in regular["results"]["rankedResults"][0]["offers"][0]
    assert debug["results"]["rankedResults"][0]["offers"][0]["rawPayload"]["fixture"]


def test_production_never_exposes_raw_payload_even_with_debug_flag(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, app_env="production"))
    response = client.post("/api/search?debug=true", json={
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy", "candidateHubs": [],
    })
    assert response.status_code == 200
    assert "rawPayload" not in str(response.json())


def test_no_results_returns_200_with_empty_arrays_and_explanation() -> None:
    response = client.post("/api/search", json={
        "originCityId": "city:sydney-au", "destinationCityId": "city:london-gb", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
        "candidateHubs": [],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "empty"
    assert body["results"]["rankedResults"] == []
    assert body["results"]["protectedItineraries"] == []
    assert body["results"]["splitTicketItineraries"] == []
    assert body["explanation"]


def test_verify_price_endpoint_must_be_called_before_booking() -> None:
    response = client.post("/api/offers/MockSky/offer-direct-mu/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert body["isConfirmed"] is True
    assert body["expiresAt"]
    assert body["checkedAt"]


def test_duffel_verify_endpoint_exists_in_mock_mode() -> None:
    response = client.post("/api/offers/Duffel/off_live_123/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["supported"] is False
    assert body["isConfirmed"] is False


def test_duffel_adapter_capability_follows_explicit_supplier_mode() -> None:
    mock_mode = build_supplier_adapters(Settings(duffel_api_token=None))
    sandbox_mode = build_supplier_adapters(Settings(
        enable_mock_supplier=False, duffel_mode="sandbox", duffel_api_token="duffel_test_token"
    ))
    mock_duffel = next(adapter for adapter in mock_mode if adapter.name.value == "Duffel")
    sandbox_duffel = next(adapter for adapter in sandbox_mode if adapter.name.value == "Duffel")
    assert mock_duffel.capabilities.supports_search is False
    assert sandbox_duffel.capabilities.supports_search is True


def test_live_mode_adapter_list_contains_no_mock_search_supplier() -> None:
    adapters = build_supplier_adapters(Settings(
        enable_mock_supplier=False,
        duffel_mode="live",
        duffel_api_token="duffel_live_authorised_fixture",
    ))
    searchable = {adapter.name for adapter in adapters if adapter.capabilities.supports_search}
    assert searchable == {main_module.Supplier.duffel}


def _booking_option(search_response, offer_fragment: str):
    itineraries = (
        search_response["results"]["protectedItineraries"]
        + search_response["results"]["splitTicketItineraries"]
    )
    for itinerary in itineraries:
        for option in itinerary["bookingOptions"]:
            if offer_fragment in (option.get("offerId") or ""):
                return itinerary, option
    raise AssertionError(f"No booking option contains {offer_fragment}")


def _search_response():
    return client.post("/api/search", json={
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy",
    }).json()


def test_pre_booking_verification_uses_canonical_option_and_records_events() -> None:
    search_body = {
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    }
    search_response = client.post("/api/search", json=search_body).json()
    search_id = search_response["searchId"]
    itinerary, option = _booking_option(search_response, "direct-mu")
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_id,
        "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["stillAvailable"] is True
    assert body["currentPrice"] == 1120
    assert body["previousPrice"] == 1120
    assert body["priceChanged"] is False
    assert body["bookingUrl"] is None
    session = SessionLocal()
    try:
        events = session.scalars(
            select(SearchEventRecord).where(SearchEventRecord.search_id == search_id)
        ).all()
        event_types = {event.event_type for event in events}
        assert {"booking_option_clicked", "verification_started", "verification_succeeded"} <= event_types
    finally:
        session.close()


def test_pre_booking_price_changed_uses_supplier_result() -> None:
    search_response = _search_response()
    itinerary, option = _booking_option(search_response, "direct-sha")
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"],
        "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["priceChanged"] is True
    assert body["currentPrice"] == body["previousPrice"] + 45
    assert body["status"] == "increased"


def test_pre_booking_unavailable_disables_continue() -> None:
    search_response = _search_response()
    itinerary, option = _booking_option(search_response, "direct-qf")
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"],
        "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["stillAvailable"] is False
    assert body["canContinue"] is False
    assert body["bookingUrl"] is None
    assert body["currentPrice"] is None


def test_unsupported_verification_requires_explicit_provider_confirmation() -> None:
    search_response = _search_response()
    search_id = search_response["searchId"]
    itinerary_id = search_response["results"]["rankedResults"][0]["id"]
    option = BookingOption(
        id="redirect-only", type=BookingOptionType.supplier, label="Provider redirect",
        supplier=Supplier.mock_sky, url="http://localhost:9999/book",
        priceStatus=PriceStatus.redirect_only,
        capabilities=SupplierCapabilities(supports_booking_url=True),
        verificationRequired=False,
    )
    main_module.service._booking_registry[search_id][option.id] = (itinerary_id, option)
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_id,
        "itineraryId": itinerary_id,
        "bookingOptionId": option.id,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["stillAvailable"] is True
    assert body["canContinue"] is True
    assert body["requiresPriceCheck"] is True
    assert body["currentPrice"] is None
    assert body["priceChanged"] is False
    assert body["status"] == "unsupported"
    assert body["message"] == "VERIFY_UNSUPPORTED"
    redirect = client.post("/api/booking-options/redirect-confirmed", json={
        "searchId": search_id,
        "itineraryId": itinerary_id,
        "bookingOptionId": option.id,
    })
    assert redirect.status_code == 200
    assert redirect.json()["bookingUrl"] == "http://localhost:9999/book"
    session = SessionLocal()
    try:
        events = session.scalars(
            select(SearchEventRecord).where(SearchEventRecord.search_id == search_id)
        ).all()
        event_types = {event.event_type for event in events}
        assert {"booking_option_clicked", "verification_failed", "provider_redirect_confirmed"} <= event_types
    finally:
        session.close()


def test_pre_booking_price_decreased_is_bound_to_canonical_option() -> None:
    search_response = _search_response()
    itinerary, option = _booking_option(search_response, "mel-bkk")
    body = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"], "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    }).json()
    assert body["status"] == "decreased"
    assert body["currentPrice"] == body["previousPrice"] - 20


@pytest.mark.parametrize(
    ("supplier_status", "expected"),
    [(VerificationStatus.timeout, "timeout"), (VerificationStatus.expired, "expired")],
)
def test_pre_booking_maps_timeout_and_expired_without_confirming(
    monkeypatch, supplier_status: VerificationStatus, expected: str
) -> None:
    search_response = _search_response()
    itinerary, option = _booking_option(search_response, "direct-mu")
    monkeypatch.setattr(
        main_module.supplier_orchestrator,
        "verify_price",
        lambda *_: VerifyPriceResult(
            offerId=option["offerId"], supplier=Supplier.mock_sky,
            status=supplier_status, checkedAt=datetime.now(timezone.utc), message="internal",
        ),
    )
    body = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"], "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    }).json()
    assert body["status"] == expected
    assert body["stillAvailable"] is False
    assert body["canContinue"] is False
    assert body["bookingUrl"] is None


def test_pre_booking_rejects_client_supplied_redirect_url() -> None:
    response = client.post("/api/booking-options/verify", json={
        "searchId": "unknown", "itineraryId": "unknown", "bookingOptionId": "unknown",
        "bookingUrl": "javascript:alert(1)",
    })
    assert response.status_code == 422


def test_pre_booking_rejects_option_bound_to_another_itinerary() -> None:
    search_response = _search_response()
    itinerary, option = _booking_option(search_response, "direct-mu")
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"],
        "itineraryId": f"{itinerary['id']}-tampered",
        "bookingOptionId": option["id"],
    })
    assert response.status_code == 404
