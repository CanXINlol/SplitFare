from __future__ import annotations

from dataclasses import replace
from math import asin, cos, radians, sin, sqrt
from urllib.parse import quote
from uuid import uuid4

from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.cities import COUNTRIES, city_service
from app.data.airport_geo import AIRPORT_GEO
from app.data.provider_search import PROVIDERS, ProviderConfig
from app.data.route_hubs import HUBS, REGIONAL_HUBS, HubConfig
from app.models import (
    CandidateRoute,
    ProviderLinkType,
    ProviderSearchLink,
    RouteDiscoveryMetadata,
    RouteDiscoveryRequest,
    RouteDiscoveryResponse,
    RouteRisk,
    RouteSort,
    SearchStatus,
    risk_level_for_score,
)


EARTH_RADIUS_KM = 6371.0088
MAX_DETOUR_RATIO = 1.75


def is_extreme_detour(ratio: float) -> bool:
    return ratio > MAX_DETOUR_RATIO


def great_circle_km(origin: str, destination: str) -> float:
    first = AIRPORT_GEO.get(origin)
    second = AIRPORT_GEO.get(destination)
    if first is None or second is None:
        raise ValueError("airport_coordinates_unavailable")
    lat1, lon1, lat2, lon2 = map(
        radians, (first.latitude, first.longitude, second.latitude, second.longitude)
    )
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * asin(sqrt(value))


def detour_ratio(origin: str, hub: str, destination: str) -> tuple[float, int, int]:
    direct = great_circle_km(origin, destination)
    split = great_circle_km(origin, hub) + great_circle_km(hub, destination)
    return max(1.0, split / direct), round(direct), round(split)


def route_signature(origin: str, hub_arrival: str, hub_departure: str, destination: str) -> str:
    hub = hub_arrival if hub_arrival == hub_departure else f"{hub_arrival}>{hub_departure}"
    return f"{origin}|{hub}|{destination}"


def _continent_for_city(city_id: str) -> str:
    city = city_service.cities[city_id]
    country = next(item for item in COUNTRIES if item.country_id == city.country_id)
    return country.continent_id


def select_hubs(origin_city_id: str, destination_city_id: str) -> tuple[HubConfig, ...]:
    pair = (_continent_for_city(origin_city_id), _continent_for_city(destination_city_id))
    preferred_codes = REGIONAL_HUBS.get(pair)
    if preferred_codes is None:
        preferred_codes = tuple(code for hub in HUBS for code in hub.airport_codes)
    order = {code: index for index, code in enumerate(preferred_codes)}
    selected = [
        hub for hub in HUBS
        if hub.enabled
        and hub.hub_city_id not in {origin_city_id, destination_city_id}
        and any(code in order for code in hub.airport_codes)
    ]
    return tuple(sorted(selected, key=lambda hub: min(order.get(code, 999) for code in hub.airport_codes)))


def _safe_https_url(value: str) -> HttpUrl | None:
    try:
        url = TypeAdapter(HttpUrl).validate_python(value)
    except ValidationError:
        return None
    host = (url.host or "").lower()
    if url.scheme != "https" or host in {"example.com", "www.example.com", "example.invalid"}:
        return None
    return url


def build_provider_link(
    config: ProviderConfig,
    *,
    link_id: str,
    origin: str,
    destination: str,
    request: RouteDiscoveryRequest,
) -> ProviderSearchLink:
    url_value = config.base_url
    link_type = ProviderLinkType.manual_search_required
    warnings = ["PROVIDER_PRICE_CONTROLS", "MANUAL_INPUT_REQUIRED"]
    if config.supports_prefilled_route and config.route_template:
        url_value = config.route_template.format(
            origin=quote(origin), destination=quote(destination),
            date=request.departure_date.isoformat(), passengers=request.passengers,
            cabin=quote(request.cabin.value),
        )
        link_type = ProviderLinkType.flight_search
        warnings = ["PROVIDER_PRICE_CONTROLS", "PREFILL_NOT_GUARANTEED"]
    elif not url_value:
        link_type = ProviderLinkType.provider_homepage
    return ProviderSearchLink(
        id=link_id,
        provider=config.provider_id,
        provider_display_name=config.display_name,
        origin_airport=origin,
        destination_airport=destination,
        departure_date=request.departure_date,
        passengers=request.passengers,
        cabin=request.cabin,
        search_url=_safe_https_url(url_value),
        link_type=link_type,
        supported_locale=list(config.supported_locales),
        warnings=warnings,
    )


def _links_for_leg(
    route_id: str,
    leg: int,
    origin: str,
    destination: str,
    request: RouteDiscoveryRequest,
    provider_configs: tuple[ProviderConfig, ...],
) -> list[ProviderSearchLink]:
    airport_country: dict[str, str] = {}
    country_codes = {country.country_id: country.country_code for country in COUNTRIES}
    for city in city_service.cities.values():
        for code in city.airport_codes:
            airport_country[code] = country_codes[city.country_id]
    route_countries = {airport_country.get(origin), airport_country.get(destination)} - {None}
    return [
        build_provider_link(
            provider, link_id=f"{route_id}:leg-{leg}:{provider.provider_id}",
            origin=origin, destination=destination, request=request,
        )
        for provider in provider_configs
        if provider.enabled
        and (not provider.supported_countries or bool(route_countries & set(provider.supported_countries)))
    ]


def _risk(cross_airport: bool, multi_airport_complexity: bool) -> RouteRisk:
    score = 45 + 10 + 10 + (35 if cross_airport else 0) + (5 if multi_airport_complexity else 0)
    score = min(100, score)
    structural = ["SELF_TRANSFER", "SEPARATE_TICKETS", "BAGGAGE_RECHECK_POSSIBLE"]
    if cross_airport:
        structural.extend(["CROSS_AIRPORT_TRANSFER", "GROUND_TRANSFER_NOT_INCLUDED"])
    return RouteRisk(
        structural_score=score,
        level=risk_level_for_score(score),
        structural_warnings=structural,
        schedule_dependent_warnings=["SCHEDULE_NOT_CHECKED", "VERIFY_GAP_ON_PROVIDER"],
        unknown_warnings=["IMMIGRATION_UNKNOWN", "TRANSIT_RULES_UNKNOWN"],
    )


def _candidate_hub_pairs(hub: HubConfig) -> tuple[tuple[str, str], ...]:
    same = [(code, code) for code in hub.airport_codes]
    cross = []
    if hub.cross_airport_risk and len(hub.airport_codes) > 1:
        cross = [(hub.airport_codes[0], hub.airport_codes[1])]
    return tuple(same + cross)


def _route_sort_key(route: CandidateRoute, sort: RouteSort) -> tuple[float, ...]:
    if sort == RouteSort.lowest_risk:
        return (route.risk.structural_score, route.detour_ratio, -route.route_score)
    if sort == RouteSort.shortest_detour:
        return (route.detour_ratio, route.risk.structural_score, -route.route_score)
    if sort == RouteSort.simplest_transfer:
        return (float(route.cross_airport), route.risk.structural_score, route.detour_ratio)
    return (-route.route_score, route.risk.structural_score, route.detour_ratio)


def discover_routes(
    request: RouteDiscoveryRequest,
    *,
    provider_configs: tuple[ProviderConfig, ...] = PROVIDERS,
) -> RouteDiscoveryResponse:
    origin = city_service.resolve(request.origin_city_id)
    destination = city_service.resolve(request.destination_city_id)
    hubs = select_hubs(origin.city_id, destination.city_id)
    routes: dict[str, CandidateRoute] = {}
    filtered = 0
    for origin_airport in origin.airports:
        for destination_airport in destination.airports:
            for hub in hubs:
                for hub_arrival, hub_departure in _candidate_hub_pairs(hub):
                    if len({origin_airport.iata_code, hub_arrival, destination_airport.iata_code}) < 3:
                        continue
                    if hub_departure in {origin_airport.iata_code, destination_airport.iata_code}:
                        continue
                    cross = hub_arrival != hub_departure
                    suggested_min = max(request.min_gap_hours, 6 if cross else 3)
                    if suggested_min > request.max_gap_hours:
                        continue
                    ratio, direct_km, split_km = detour_ratio(
                        origin_airport.iata_code, hub_arrival, destination_airport.iata_code
                    )
                    if cross:
                        split_km += round(great_circle_km(hub_arrival, hub_departure))
                        ratio = max(1.0, split_km / direct_km)
                    if is_extreme_detour(ratio):
                        filtered += 1
                        continue
                    signature = route_signature(
                        origin_airport.iata_code, hub_arrival, hub_departure,
                        destination_airport.iata_code,
                    )
                    if signature in routes:
                        continue
                    route_id = f"route:{signature.replace('|', '-').replace('>', '-to-').lower()}"
                    risk = _risk(cross, len(origin.airports) > 1 or len(destination.airports) > 1)
                    detour_penalty = min(45, (ratio - 1) * 80)
                    route_score = max(
                        0, min(100, 45 + hub.international_connectivity_score * 0.45
                                   - detour_penalty - risk.structural_score * 0.18
                                   - (12 if cross else 0) - hub.priority)
                    )
                    detour_level = "low" if ratio <= 1.15 else "moderate" if ratio <= 1.4 else "high"
                    reasons = ["MAJOR_HUB", f"DETOUR_{detour_level.upper()}"]
                    if not cross:
                        reasons.append("SAME_AIRPORT_TRANSFER")
                    if hub.overnight_suitability == "good":
                        reasons.append("OVERNIGHT_OPTION_POSSIBLE")
                    first_links = _links_for_leg(
                        route_id, 1, origin_airport.iata_code, hub_arrival,
                        request, provider_configs,
                    )
                    second_links = _links_for_leg(
                        route_id, 2, hub_departure, destination_airport.iata_code,
                        request, provider_configs,
                    )
                    full_provider = next(
                        (item for item in provider_configs if item.provider_id == "google-flights"),
                        None,
                    )
                    full_links = [] if full_provider is None else [build_provider_link(
                        replace(full_provider, supports_prefilled_route=False),
                        link_id=f"{route_id}:full:{full_provider.provider_id}",
                        origin=origin_airport.iata_code,
                        destination=destination_airport.iata_code,
                        request=request,
                    )]
                    routes[signature] = CandidateRoute(
                        id=route_id, signature=signature,
                        origin_city_id=origin.city_id, destination_city_id=destination.city_id,
                        origin_airport=origin_airport.iata_code,
                        hub_city_id=hub.hub_city_id,
                        hub_arrival_airport=hub_arrival,
                        hub_departure_airport=hub_departure,
                        destination_airport=destination_airport.iata_code,
                        departure_date=request.departure_date,
                        suggested_min_gap_hours=suggested_min,
                        suggested_max_gap_hours=request.max_gap_hours,
                        cross_airport=cross,
                        direct_distance_km=direct_km, split_distance_km=split_km,
                        detour_ratio=round(ratio, 3), detour_level=detour_level,
                        route_score=round(route_score, 2), risk=risk,
                        recommendation_reasons=reasons,
                        first_leg_links=first_links, second_leg_links=second_links,
                        full_route_links=full_links,
                    )
    ranked = sorted(routes.values(), key=lambda item: _route_sort_key(item, request.sort))
    ranked = ranked[:request.max_results]
    return RouteDiscoveryResponse(
        discovery_id=str(uuid4()),
        status=SearchStatus.complete if ranked else SearchStatus.empty,
        routes=ranked,
        metadata=RouteDiscoveryMetadata(
            origin_airports=[item.iata_code for item in origin.airports],
            destination_airports=[item.iata_code for item in destination.airports],
            selected_hubs=[hub.hub_city_id for hub in hubs],
            generated_route_count=len(routes),
            filtered_extreme_detour_count=filtered,
        ),
    )
