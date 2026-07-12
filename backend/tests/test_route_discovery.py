from datetime import date

import pytest
from pydantic import ValidationError

from app.data.provider_search import ProviderConfig
from app.models import (
    ProviderLinkType,
    ProviderSearchLink,
    RiskLevel,
    RouteDiscoveryRequest,
    RouteSort,
)
from app.route_discovery import (
    build_provider_link,
    detour_ratio,
    discover_routes,
    great_circle_km,
    is_extreme_detour,
    route_signature,
    select_hubs,
)


def request(**updates) -> RouteDiscoveryRequest:
    return RouteDiscoveryRequest(**({
        "originCityId": "city:melbourne-au", "destinationCityId": "city:shanghai-cn",
        "departureDate": date(2026, 8, 12), "minGapHours": 3, "maxGapHours": 12,
        "passengers": 1, "cabin": "economy", "maxResults": 50,
    } | updates))


def test_melbourne_shanghai_generates_candidate_routes_for_real_airports() -> None:
    response = discover_routes(request())
    assert response.routes
    assert {item.origin_airport for item in response.routes} == {"MEL", "AVV"}
    assert {item.destination_airport for item in response.routes} == {"PVG", "SHA"}
    assert all(item.candidate_route for item in response.routes)
    assert response.metadata.price_data_available is False


def test_routes_have_two_provider_link_sets_without_prices_or_flight_times() -> None:
    route = discover_routes(request(maxResults=1)).routes[0]
    assert route.first_leg_links and route.second_leg_links
    assert all(link.search_url and link.search_url.scheme == "https" for link in route.first_leg_links)
    serialized = route.model_dump(mode="json", by_alias=True)
    assert "priceAmount" not in serialized
    assert "departureAt" not in serialized
    assert "flightNumber" not in serialized


def test_same_city_is_rejected() -> None:
    with pytest.raises(ValidationError):
        request(destinationCityId="city:melbourne-au")


def test_regional_hubs_change_with_route_region() -> None:
    oceania_asia = {hub.hub_city_id for hub in select_hubs("city:melbourne-au", "city:shanghai-cn")}
    north_america_asia = {hub.hub_city_id for hub in select_hubs("city:new-york-us", "city:tokyo-jp")}
    assert "city:singapore-sg" in oceania_asia
    assert "city:vancouver-ca" in north_america_asia
    assert oceania_asia != north_america_asia


def test_great_circle_distance_and_detour_ratio_are_stable() -> None:
    assert 7900 < great_circle_km("MEL", "PVG") < 8300
    ratio, direct, split = detour_ratio("MEL", "SIN", "PVG")
    assert ratio >= 1
    assert split >= direct


def test_extreme_detour_rule() -> None:
    assert is_extreme_detour(1.751)
    assert not is_extreme_detour(1.75)


def test_route_signature_distinguishes_airports_and_cross_airport() -> None:
    assert route_signature("MEL", "BKK", "BKK", "PVG") == "MEL|BKK|PVG"
    assert route_signature("MEL", "BKK", "DMK", "PVG") == "MEL|BKK>DMK|PVG"
    assert route_signature("AVV", "BKK", "BKK", "PVG") != route_signature("MEL", "BKK", "BKK", "PVG")


def test_duplicate_route_signatures_are_removed() -> None:
    routes = discover_routes(request()).routes
    assert len(routes) == len({route.signature for route in routes})


def test_cross_airport_route_has_extreme_structural_risk() -> None:
    route = next(item for item in discover_routes(request()).routes if item.cross_airport)
    assert route.risk.level == RiskLevel.extreme
    assert "CROSS_AIRPORT_TRANSFER" in route.risk.structural_warnings
    assert route.hub_arrival_airport != route.hub_departure_airport


def test_schedule_is_explicitly_unknown() -> None:
    route = discover_routes(request(maxResults=1)).routes[0]
    assert {"SCHEDULE_NOT_CHECKED", "VERIFY_GAP_ON_PROVIDER"} <= set(route.risk.schedule_dependent_warnings)


def test_lowest_risk_sort_is_monotonic() -> None:
    routes = discover_routes(request(sort=RouteSort.lowest_risk)).routes
    assert [item.risk.structural_score for item in routes] == sorted(item.risk.structural_score for item in routes)


def test_shortest_detour_sort_is_monotonic() -> None:
    routes = discover_routes(request(sort=RouteSort.shortest_detour)).routes
    assert [item.detour_ratio for item in routes] == sorted(item.detour_ratio for item in routes)


def test_documented_template_support_builds_prefilled_deep_link() -> None:
    config = ProviderConfig(
        "fixture", "Fixture Search", "https://search.test/flights", (), ("en",), True, True,
        route_template="https://search.test/flights/{origin}/{destination}/{date}?adults={passengers}&cabin={cabin}",
    )
    link = build_provider_link(config, link_id="one", origin="MEL", destination="SIN", request=request())
    assert link.link_type == ProviderLinkType.flight_search
    assert "/MEL/SIN/2026-08-12" in str(link.search_url)


def test_provider_without_deep_link_uses_homepage_and_manual_warning() -> None:
    config = ProviderConfig("manual", "Manual", "https://search.test/flights", (), ("en",), False, False)
    link = build_provider_link(config, link_id="one", origin="MEL", destination="SIN", request=request())
    assert link.link_type == ProviderLinkType.manual_search_required
    assert "MANUAL_INPUT_REQUIRED" in link.warnings


def test_provider_http_and_dangerous_protocol_are_rejected() -> None:
    config = ProviderConfig("unsafe", "Unsafe", "http://unsafe.test", (), ("en",), False, False)
    assert build_provider_link(config, link_id="one", origin="MEL", destination="SIN", request=request()).search_url is None
    with pytest.raises(ValidationError):
        ProviderSearchLink(
            id="bad", provider="bad", providerDisplayName="Bad", originAirport="MEL",
            destinationAirport="SIN", departureDate="2026-08-12", passengers=1,
            cabin="economy", searchUrl="javascript:alert(1)", linkType="flight_search",
            supportedLocale=["en"], warnings=[],
        )


@pytest.mark.parametrize(
    ("origin", "destination"),
    [("city:london-gb", "city:shanghai-cn"), ("city:new-york-us", "city:tokyo-jp")],
)
def test_other_regional_routes_generate(origin: str, destination: str) -> None:
    assert discover_routes(request(originCityId=origin, destinationCityId=destination, maxResults=10)).routes
