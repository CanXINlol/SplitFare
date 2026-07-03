import asyncio
from datetime import date

import pytest
from pydantic import ValidationError

from app.adapters.mock_supplier import build_mock_orchestrator
from app.models import PlaceType, SearchRequest
from app.places import place_service
from app.search import SearchService
from app.search_orchestrator import (
    MAX_HUBS,
    SearchOrchestrator,
    generate_candidate_hubs,
    generate_query_plan,
)


def request(
    origin: str = "city:melbourne-au",
    destination: str = "city:shanghai-cn",
    hubs: list[str] | None = None,
) -> SearchRequest:
    return SearchRequest(
        originPlaceId=origin,
        destinationPlaceId=destination,
        departureDate=date(2026, 8, 12),
        minGapHours=3,
        maxGapHours=12,
        passengers=1,
        cabin="economy",
        candidateHubs=hubs,
    )


def test_melbourne_search_returns_city_then_airports() -> None:
    results = place_service.search("Melbourne")
    assert [item.display_name for item in results[:3]] == [
        "Melbourne, Australia",
        "Melbourne Airport (MEL)",
        "Avalon Airport (AVV)",
    ]


def test_shanghai_search_returns_city_then_airports() -> None:
    results = place_service.search("Shanghai")
    assert [item.display_name for item in results[:3]] == [
        "Shanghai, China",
        "Shanghai Pudong Airport (PVG)",
        "Shanghai Hongqiao Airport (SHA)",
    ]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("墨尔本", "city:melbourne-au"),
        ("上海", "city:shanghai-cn"),
        ("北京", "city:beijing-cn"),
        ("广州", "city:guangzhou-cn"),
        ("深圳", "city:shenzhen-cn"),
        ("香港", "city:hong-kong-cn"),
        ("台北", "city:taipei-tw"),
        ("东京", "city:tokyo-jp"),
        ("首尔", "city:seoul-kr"),
        ("曼谷", "city:bangkok-th"),
        ("新加坡", "city:singapore-sg"),
        ("吉隆坡", "city:kuala-lumpur-my"),
        ("伦敦", "city:london-gb"),
        ("纽约", "city:new-york-us"),
    ],
)
def test_chinese_alias_matching(query: str, expected: str) -> None:
    assert place_service.search(query)[0].id == expected


def test_exact_iata_code_matching_prioritizes_airport() -> None:
    result = place_service.search("PVG")[0]
    assert result.type == PlaceType.airport
    assert result.iata_code == "PVG"


def test_startswith_matching_finds_singapore() -> None:
    assert place_service.search("Sing")[0].id == "city:singapore-sg"


def test_contains_matching_finds_kuala_lumpur() -> None:
    assert place_service.search("lumpur")[0].id == "city:kuala-lumpur-my"


def test_city_resolution_returns_prioritized_airports() -> None:
    resolved = place_service.resolve("city:shanghai-cn")
    assert [airport.iata_code for airport in resolved.airports] == ["PVG", "SHA"]


def test_airport_resolution_returns_single_airport() -> None:
    resolved = place_service.resolve("airport:PVG")
    assert resolved.type == PlaceType.airport
    assert [airport.iata_code for airport in resolved.airports] == ["PVG"]


def test_london_resolution_is_capped_to_three_airports() -> None:
    resolved = place_service.resolve("city:london-gb")
    assert [airport.iata_code for airport in resolved.airports] == ["LHR", "LGW", "STN"]


def test_invalid_place_raises_friendly_error() -> None:
    with pytest.raises(ValueError, match="Choose a city or airport"):
        place_service.resolve("place:missing")


def test_search_matrix_generates_melbourne_to_shanghai_baseline_pairs() -> None:
    matrix = place_service.build_matrix(request(), generate_candidate_hubs(request()))
    assert [(pair.origin, pair.destination) for pair in matrix.baseline_pairs] == [
        ("MEL", "PVG"),
        ("MEL", "SHA"),
        ("AVV", "PVG"),
        ("AVV", "SHA"),
    ]


def test_search_matrix_generates_split_ticket_queries_for_each_airport_pair() -> None:
    matrix = place_service.build_matrix(request(hubs=["BKK"]), ("BKK",))
    routes = {(query.origin, query.destination, query.kind) for query in matrix.query_plan}
    assert ("MEL", "BKK", "outbound_to_hub") in routes
    assert ("BKK", "PVG", "hub_to_destination") in routes
    assert ("AVV", "BKK", "outbound_to_hub") in routes
    assert ("BKK", "SHA", "hub_to_destination") in routes


def test_matrix_caps_hubs_to_twelve() -> None:
    matrix = place_service.build_matrix(request(), generate_candidate_hubs(request()))
    assert len(matrix.hubs) == MAX_HUBS


def test_airport_destination_only_searches_that_airport() -> None:
    matrix = place_service.build_matrix(request(destination="airport:PVG"), generate_candidate_hubs(request(destination="airport:PVG")))
    assert [airport.iata_code for airport in matrix.destination_airports] == ["PVG"]
    assert {pair.destination for pair in matrix.baseline_pairs} == {"PVG"}


def test_generate_query_plan_uses_airport_matrix() -> None:
    plan = generate_query_plan(request(hubs=["BKK"]))
    assert any(query.origin == "MEL" and query.destination == "PVG" for query in plan)
    assert any(query.origin == "AVV" and query.destination == "SHA" for query in plan)
    assert any(query.origin == "MEL" and query.destination == "BKK" for query in plan)


def test_same_place_is_rejected_before_matrix_generation() -> None:
    with pytest.raises(ValidationError, match="origin and destination places must differ"):
        request("airport:MEL", "airport:MEL")


def test_melbourne_shanghai_full_flow_returns_airport_specific_results() -> None:
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    response = asyncio.run(service.search(request()))
    assert response.ranked
    assert any(segment.origin == "MEL" for itinerary in response.ranked for segment in itinerary.segments)
    assert any(segment.destination in {"PVG", "SHA"} for itinerary in response.ranked for segment in itinerary.segments)
    assert response.ranked[0].segments[0].origin_display


def test_chinese_melbourne_shanghai_search_inputs_resolve_to_same_flow() -> None:
    origin = place_service.search("墨尔本")[0].id
    destination = place_service.search("上海")[0].id
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    response = asyncio.run(service.search(request(origin, destination)))
    assert response.ranked
    assert response.cheapest_split is not None


def test_gap_filtering_still_applies_after_location_resolution() -> None:
    search_request = request()
    search_request.min_gap_hours = 4
    search_request.max_gap_hours = 8
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    response = asyncio.run(service.search(search_request))
    splits = [item for item in response.ranked if item.type == "split_ticket"]
    assert splits
    assert all(240 <= (item.layover_gap_minutes or 0) <= 480 for item in splits)


def test_booking_options_survive_location_search() -> None:
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    response = asyncio.run(service.search(request()))
    assert response.ranked[0].booking_options
    assert any(option.label == "Check on Trip.com" for option in response.ranked[0].booking_options)
