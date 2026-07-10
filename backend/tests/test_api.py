from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.config import Settings
from app.db import SessionLocal
from app.db_models import SearchEventRecord
from app.main import app, build_supplier_adapters


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


def test_place_search_api_supports_english_and_chinese_aliases() -> None:
    english = client.get("/api/places/search", params={"q": "Melbourne"})
    chinese = client.get("/api/places/search", params={"q": "上海"})
    assert english.status_code == 200
    assert chinese.status_code == 200
    assert english.json()["results"][0]["id"] == "city:melbourne-au"
    assert chinese.json()["results"][0]["id"] == "city:shanghai-cn"


def test_place_resolve_api_wraps_airport_as_resolved_place() -> None:
    response = client.post("/api/places/resolve", json={"placeId": "airport:PVG"})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "airport"
    assert [airport["iataCode"] for airport in body["airports"]] == ["PVG"]


def test_place_search_api_supports_real_chinese_aliases() -> None:
    response = client.get("/api/places/search", params={"q": "\u4e0a\u6d77"})
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "city:shanghai-cn"


def test_invalid_place_returns_user_friendly_404() -> None:
    response = client.post("/api/places/resolve", json={"placeId": "place:missing"})
    assert response.status_code == 404
    assert "Choose a city or airport" in response.json()["error"]["message"]


def test_place_search_rejects_oversized_queries() -> None:
    response = client.get("/api/places/search", params={"q": "x" * 81})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rate_limit_applies_to_search_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, rate_limit_requests_per_minute=1),
    )
    main_module._rate_limit_hits.clear()
    payload = {
        "originPlaceId": "airport:SYD", "destinationPlaceId": "airport:LHR",
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
        "originPlaceId": "city:melbourne-au", "destinationPlaceId": "city:shanghai-cn", "departureDate": "2026-08-12",
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
    trip_option = next(
        option for option in body["cheapestSplit"]["bookingOptions"]
        if option["label"] == "Check on Trip.com"
    )
    assert trip_option["priceStatus"] == "redirect_only"
    assert trip_option["priceAmount"] is None
    assert "tracking_id=splitfare_demo" in trip_option["url"]
    assert body["metadata"]["demoData"] is True
    assert body["metadata"]["mode"] == "mock"
    assert body["metadata"]["supplierQueryCount"] <= body["metadata"]["supplierQueryLimit"]
    assert body["cheapestSplit"]["priceSourceCoverage"]["checkRequiredSupplierCount"] >= 1
    assert body["results"]["baselinePrice"] == body["baseline"]["totalPrice"]
    assert body["results"]["protectedItineraries"]
    assert body["results"]["splitTicketItineraries"]
    assert len(body["results"]["rankedResults"]) <= 20
    assert "rankedResults" not in body
    assert body["supplierFailures"] == []


def test_openapi_contract_uses_location_search_and_canonical_verification_fields() -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    search_properties = schemas["SearchRequest"]["properties"]
    assert "originPlaceId" in search_properties
    assert "destinationPlaceId" in search_properties
    assert "origin" not in search_properties
    assert "destination" not in search_properties
    response_required = set(schemas["SearchResponse"]["required"])
    assert {"searchId", "status", "results", "metadata", "disclaimer"} <= response_required
    verification_properties = set(schemas["PreBookingVerificationRequest"]["properties"])
    assert verification_properties == {"searchId", "itineraryId", "bookingOptionId"}


def test_raw_payload_requires_explicit_debug_flag() -> None:
    payload = {
        "originPlaceId": "city:melbourne-au", "destinationPlaceId": "city:shanghai-cn", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    }
    regular = client.post("/api/search", json=payload).json()
    debug = client.post("/api/search?debug=true", json=payload).json()
    assert "rawPayload" not in regular["results"]["rankedResults"][0]["offers"][0]
    assert debug["results"]["rankedResults"][0]["offers"][0]["rawPayload"]["fixture"]


def test_production_never_exposes_raw_payload_even_with_debug_flag(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, app_env="production"))
    response = client.post("/api/search?debug=true", json={
        "originPlaceId": "airport:MEL", "destinationPlaceId": "airport:PVG",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy", "candidateHubs": [],
    })
    assert response.status_code == 200
    assert "rawPayload" not in str(response.json())


def test_no_results_returns_200_with_empty_arrays_and_explanation() -> None:
    response = client.post("/api/search", json={
        "originPlaceId": "airport:SYD", "destinationPlaceId": "airport:LHR", "departureDate": "2026-08-12",
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


def test_live_duffel_adapter_is_only_enabled_when_token_exists() -> None:
    mock_mode = build_supplier_adapters(Settings(duffel_api_token=None))
    live_mode = build_supplier_adapters(Settings(
        enable_mock_supplier=False, duffel_api_token="duffel_test_token"
    ))
    mock_duffel = next(adapter for adapter in mock_mode if adapter.name.value == "Duffel")
    live_duffel = next(adapter for adapter in live_mode if adapter.name.value == "Duffel")
    assert mock_duffel.capabilities.supports_search is False
    assert live_duffel.capabilities.supports_search is True


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
        "originPlaceId": "city:melbourne-au", "destinationPlaceId": "city:shanghai-cn",
        "departureDate": "2026-08-12", "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy",
    }).json()


def test_pre_booking_verification_uses_canonical_option_and_records_events() -> None:
    search_body = {
        "originPlaceId": "city:melbourne-au", "destinationPlaceId": "city:shanghai-cn", "departureDate": "2026-08-12",
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
        assert "booking.clicked" in {event.event_type for event in events}
        assert "booking.verification_completed" in {event.event_type for event in events}
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


def test_trip_com_pre_booking_requires_provider_price_check() -> None:
    search_response = _search_response()
    itinerary = search_response["results"]["rankedResults"][0]
    option = next(item for item in itinerary["bookingOptions"] if item["type"] == "trip_com")
    response = client.post("/api/booking-options/verify", json={
        "searchId": search_response["searchId"],
        "itineraryId": itinerary["id"],
        "bookingOptionId": option["id"],
    })
    assert response.status_code == 200
    body = response.json()
    assert body["stillAvailable"] is True
    assert body["canContinue"] is True
    assert body["requiresPriceCheck"] is True
    assert body["currentPrice"] is None
    assert body["priceChanged"] is False
    assert body["status"] == "unsupported"


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
