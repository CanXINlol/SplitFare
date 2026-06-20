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
    assert body["baseline"]["totalPrice"] > 0
    assert body["cheapestSplit"]["type"] == "split_ticket"
    offer = body["cheapestSplit"]["offers"][0]
    assert set({
        "id", "supplier", "origin", "destination", "departureAt", "arrivalAt",
        "airline", "operatingAirline", "flightNumber", "priceAmount", "currency",
        "cabin", "baggageIncluded", "bookingUrl", "rawPayload", "lastCheckedAt", "expiresAt",
    }).issubset(offer)
    assert body["cheapestSplit"]["riskAssessment"]["score"] == body["cheapestSplit"]["riskScore"]
    assert body["baselinePrice"] == body["baseline"]["totalPrice"]
    assert body["protectedItineraries"]
    assert body["splitTicketItineraries"]
    assert len(body["rankedResults"]) <= 20
    assert body["rankedResults"] == body["ranked"]
