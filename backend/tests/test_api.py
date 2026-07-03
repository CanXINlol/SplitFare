from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, build_supplier_adapters


client = TestClient(app)


def test_search_api_uses_camel_case_contract() -> None:
    response = client.post("/api/search", json={
        "origin": "MEL", "destination": "PVG", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["searchId"]
    assert body["status"] == "complete"
    assert body["results"]["rankedResults"] == body["rankedResults"]
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
    assert body["baselinePrice"] == body["baseline"]["totalPrice"]
    assert body["protectedItineraries"]
    assert body["splitTicketItineraries"]
    assert len(body["rankedResults"]) <= 20
    assert body["rankedResults"] == body["ranked"]
    assert body["supplierFailures"] == []


def test_raw_payload_requires_explicit_debug_flag() -> None:
    payload = {
        "origin": "MEL", "destination": "PVG", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    }
    regular = client.post("/api/search", json=payload).json()
    debug = client.post("/api/search?debug=true", json=payload).json()
    assert "rawPayload" not in regular["rankedResults"][0]["offers"][0]
    assert debug["rankedResults"][0]["offers"][0]["rawPayload"]["fixture"]


def test_no_results_returns_200_with_empty_arrays_and_explanation() -> None:
    response = client.post("/api/search", json={
        "origin": "AAA", "destination": "BBB", "departureDate": "2026-08-12",
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
    assert body["status"] == "not_configured"
    assert body["isConfirmed"] is False


def test_live_duffel_adapter_is_only_enabled_when_token_exists() -> None:
    mock_mode = build_supplier_adapters(Settings(duffel_api_token=None))
    live_mode = build_supplier_adapters(Settings(duffel_api_token="duffel_test_token"))
    assert "Duffel" not in {adapter.name.value for adapter in mock_mode}
    assert "Duffel" in {adapter.name.value for adapter in live_mode}
