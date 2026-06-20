from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_search_api_uses_camel_case_contract() -> None:
    response = client.post("/api/search", json={
        "origin": "MEL", "destination": "PVG", "departureDate": "2026-08-12",
        "minGapHours": 3, "maxGapHours": 12, "passengers": 1, "cabin": "economy",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["searchId"]
    assert body["status"] == "partial"
    assert body["results"]["rankedResults"] == body["rankedResults"]
    assert body["errors"]
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
    assert body["baselinePrice"] == body["baseline"]["totalPrice"]
    assert body["protectedItineraries"]
    assert body["splitTicketItineraries"]
    assert len(body["rankedResults"]) <= 20
    assert body["rankedResults"] == body["ranked"]
    assert {failure["supplier"] for failure in body["supplierFailures"]} == {"Duffel", "Skyscanner"}


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
