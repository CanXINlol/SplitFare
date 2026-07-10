from datetime import date

import pytest
from pydantic import ValidationError

from app.cities import city_service
from app.models import SearchRequest
from app.search_orchestrator import generate_candidate_hubs


def request(origin: str = "city:melbourne-au", destination: str = "city:shanghai-cn") -> SearchRequest:
    return SearchRequest(
        originCityId=origin,
        destinationCityId=destination,
        departureDate=date(2026, 8, 12),
        minGapHours=3,
        maxGapHours=12,
        passengers=1,
        cabin="economy",
    )


def test_catalog_has_required_hierarchy_and_bilingual_names() -> None:
    catalog = city_service.catalog()
    assert {item.continent_id for item in catalog.continents} == {"asia", "oceania", "europe", "north-america"}
    assert all(item.continent_name_zh and item.continent_name_en for item in catalog.continents)
    assert all(item.country_name_zh and item.country_name_en for item in catalog.countries)
    assert all(item.city_name_zh and item.city_name_en for item in catalog.cities)


def test_every_enabled_city_has_an_airport() -> None:
    assert all(city.airport_codes for city in city_service.catalog().cities if city.enabled)


def test_airport_codes_do_not_belong_to_multiple_cities() -> None:
    codes = [code for city in city_service.catalog().cities for code in city.airport_codes]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize(
    ("city_id", "codes"),
    [
        ("city:melbourne-au", ["MEL", "AVV"]),
        ("city:shanghai-cn", ["PVG", "SHA"]),
        ("city:beijing-cn", ["PEK", "PKX"]),
        ("city:tokyo-jp", ["HND", "NRT"]),
        ("city:auckland-nz", ["AKL"]),
        ("city:toronto-ca", ["YYZ"]),
    ],
)
def test_city_resolves_to_expected_airport_set(city_id: str, codes: list[str]) -> None:
    assert [airport.iata_code for airport in city_service.resolve(city_id).airports] == codes


def test_invalid_city_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid_city_id"):
        city_service.resolve("city:missing")


def test_airport_id_is_not_a_valid_city_id() -> None:
    with pytest.raises(ValidationError):
        request(destination="airport:PVG")


def test_same_city_is_rejected() -> None:
    with pytest.raises(ValidationError):
        request(destination="city:melbourne-au")


def test_melbourne_shanghai_matrix_contains_all_four_baselines() -> None:
    search = request()
    matrix = city_service.build_matrix(search, generate_candidate_hubs(search))
    assert {(q.origin, q.destination) for q in matrix.baseline_pairs} == {
        ("MEL", "PVG"), ("MEL", "SHA"), ("AVV", "PVG"), ("AVV", "SHA")
    }


def test_matrix_hubs_are_capped_and_exclude_endpoints() -> None:
    search = request()
    matrix = city_service.build_matrix(search, tuple(["MEL", "PVG", "BKK", "SIN", "KUL", "HKG", "TPE", "ICN", "NRT", "KIX", "CAN", "SZX", "MNL", "SGN"]))
    assert len(matrix.hubs) <= 12
    assert not ({"MEL", "PVG"} & {item.iata_code for item in matrix.hubs})


def test_large_city_airport_set_is_priority_truncated() -> None:
    resolved = city_service.resolve("city:london-gb")
    assert [item.iata_code for item in resolved.airports] == ["LHR", "LGW", "STN"]


def test_catalog_version_is_explicit() -> None:
    assert city_service.catalog().version == "city-catalog-v1"
