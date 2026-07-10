from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.data.mock_flights import MOCK_FLIGHTS
from app.models import (
    AirportSearchMatrix,
    CandidateAirport,
    City,
    CityCatalog,
    Continent,
    Country,
    FlightQuery,
    ResolvedCity,
    SearchRequest,
)


CATALOG_VERSION = "city-catalog-v1"
MAX_ORIGIN_AIRPORTS = 3
MAX_DESTINATION_AIRPORTS = 3
MAX_MATRIX_HUBS = 12
MAX_ROUTE_QUERIES = 120


CONTINENTS = (
    Continent(continent_id="asia", continent_name_zh="亚洲", continent_name_en="Asia", priority=1),
    Continent(continent_id="oceania", continent_name_zh="大洋洲", continent_name_en="Oceania", priority=2),
    Continent(continent_id="europe", continent_name_zh="欧洲", continent_name_en="Europe", priority=3),
    Continent(continent_id="north-america", continent_name_zh="北美洲", continent_name_en="North America", priority=4),
)

COUNTRIES = (
    Country(country_id="china", continent_id="asia", country_name_zh="中国", country_name_en="China", country_code="CN", priority=1),
    Country(country_id="japan", continent_id="asia", country_name_zh="日本", country_name_en="Japan", country_code="JP", priority=2),
    Country(country_id="south-korea", continent_id="asia", country_name_zh="韩国", country_name_en="South Korea", country_code="KR", priority=3),
    Country(country_id="thailand", continent_id="asia", country_name_zh="泰国", country_name_en="Thailand", country_code="TH", priority=4),
    Country(country_id="singapore", continent_id="asia", country_name_zh="新加坡", country_name_en="Singapore", country_code="SG", priority=5),
    Country(country_id="malaysia", continent_id="asia", country_name_zh="马来西亚", country_name_en="Malaysia", country_code="MY", priority=6),
    Country(country_id="taiwan", continent_id="asia", country_name_zh="中国台湾", country_name_en="Taiwan, China", country_code="TW", priority=7),
    Country(country_id="vietnam", continent_id="asia", country_name_zh="越南", country_name_en="Vietnam", country_code="VN", priority=8),
    Country(country_id="philippines", continent_id="asia", country_name_zh="菲律宾", country_name_en="Philippines", country_code="PH", priority=9),
    Country(country_id="australia", continent_id="oceania", country_name_zh="澳大利亚", country_name_en="Australia", country_code="AU", priority=1),
    Country(country_id="new-zealand", continent_id="oceania", country_name_zh="新西兰", country_name_en="New Zealand", country_code="NZ", priority=2),
    Country(country_id="united-kingdom", continent_id="europe", country_name_zh="英国", country_name_en="United Kingdom", country_code="GB", priority=1),
    Country(country_id="france", continent_id="europe", country_name_zh="法国", country_name_en="France", country_code="FR", priority=2),
    Country(country_id="germany", continent_id="europe", country_name_zh="德国", country_name_en="Germany", country_code="DE", priority=3),
    Country(country_id="united-states", continent_id="north-america", country_name_zh="美国", country_name_en="United States", country_code="US", priority=1),
    Country(country_id="canada", continent_id="north-america", country_name_zh="加拿大", country_name_en="Canada", country_code="CA", priority=2),
)


@dataclass(frozen=True)
class CitySeed:
    city_id: str
    zh: str
    en: str
    country_id: str
    airports: tuple[str, ...]
    priority: int = 1


CITY_SEEDS = (
    CitySeed("city:shanghai-cn", "上海", "Shanghai", "china", ("PVG", "SHA")),
    CitySeed("city:beijing-cn", "北京", "Beijing", "china", ("PEK", "PKX")),
    CitySeed("city:guangzhou-cn", "广州", "Guangzhou", "china", ("CAN",)),
    CitySeed("city:shenzhen-cn", "深圳", "Shenzhen", "china", ("SZX",)),
    CitySeed("city:hangzhou-cn", "杭州", "Hangzhou", "china", ("HGH",), 2),
    CitySeed("city:nanjing-cn", "南京", "Nanjing", "china", ("NKG",), 2),
    CitySeed("city:chengdu-cn", "成都", "Chengdu", "china", ("TFU", "CTU"), 2),
    CitySeed("city:hong-kong-cn", "香港", "Hong Kong", "china", ("HKG",)),
    CitySeed("city:tokyo-jp", "东京", "Tokyo", "japan", ("HND", "NRT")),
    CitySeed("city:osaka-jp", "大阪", "Osaka", "japan", ("KIX",), 2),
    CitySeed("city:seoul-kr", "首尔", "Seoul", "south-korea", ("ICN", "GMP")),
    CitySeed("city:bangkok-th", "曼谷", "Bangkok", "thailand", ("BKK", "DMK")),
    CitySeed("city:singapore-sg", "新加坡", "Singapore", "singapore", ("SIN",)),
    CitySeed("city:kuala-lumpur-my", "吉隆坡", "Kuala Lumpur", "malaysia", ("KUL",)),
    CitySeed("city:taipei-tw", "台北", "Taipei", "taiwan", ("TPE",)),
    CitySeed("city:ho-chi-minh-vn", "胡志明市", "Ho Chi Minh City", "vietnam", ("SGN",)),
    CitySeed("city:hanoi-vn", "河内", "Hanoi", "vietnam", ("HAN",), 2),
    CitySeed("city:manila-ph", "马尼拉", "Manila", "philippines", ("MNL",)),
    CitySeed("city:melbourne-au", "墨尔本", "Melbourne", "australia", ("MEL", "AVV")),
    CitySeed("city:sydney-au", "悉尼", "Sydney", "australia", ("SYD",)),
    CitySeed("city:brisbane-au", "布里斯班", "Brisbane", "australia", ("BNE",), 2),
    CitySeed("city:perth-au", "珀斯", "Perth", "australia", ("PER",), 2),
    CitySeed("city:adelaide-au", "阿德莱德", "Adelaide", "australia", ("ADL",), 2),
    CitySeed("city:auckland-nz", "奥克兰", "Auckland", "new-zealand", ("AKL",)),
    CitySeed("city:christchurch-nz", "基督城", "Christchurch", "new-zealand", ("CHC",), 2),
    CitySeed("city:london-gb", "伦敦", "London", "united-kingdom", ("LHR", "LGW", "STN", "LTN", "LCY")),
    CitySeed("city:paris-fr", "巴黎", "Paris", "france", ("CDG", "ORY")),
    CitySeed("city:frankfurt-de", "法兰克福", "Frankfurt", "germany", ("FRA",)),
    CitySeed("city:new-york-us", "纽约", "New York", "united-states", ("JFK", "EWR", "LGA")),
    CitySeed("city:los-angeles-us", "洛杉矶", "Los Angeles", "united-states", ("LAX",)),
    CitySeed("city:san-francisco-us", "旧金山", "San Francisco", "united-states", ("SFO",), 2),
    CitySeed("city:toronto-ca", "多伦多", "Toronto", "canada", ("YYZ",)),
    CitySeed("city:vancouver-ca", "温哥华", "Vancouver", "canada", ("YVR",), 2),
)


AIRPORT_NAMES = {
    "MEL": "Melbourne Airport", "AVV": "Avalon Airport", "SYD": "Sydney Airport",
    "BNE": "Brisbane Airport", "PER": "Perth Airport", "ADL": "Adelaide Airport",
    "AKL": "Auckland Airport", "CHC": "Christchurch Airport",
    "PVG": "Shanghai Pudong Airport", "SHA": "Shanghai Hongqiao Airport",
    "PEK": "Beijing Capital Airport", "PKX": "Beijing Daxing Airport",
    "CAN": "Guangzhou Baiyun Airport", "SZX": "Shenzhen Bao'an Airport",
    "HGH": "Hangzhou Xiaoshan Airport", "NKG": "Nanjing Lukou Airport",
    "CTU": "Chengdu Shuangliu Airport", "TFU": "Chengdu Tianfu Airport",
    "HKG": "Hong Kong International Airport", "HND": "Tokyo Haneda Airport",
    "NRT": "Tokyo Narita Airport", "KIX": "Osaka Kansai Airport",
    "ICN": "Seoul Incheon Airport", "GMP": "Seoul Gimpo Airport",
    "BKK": "Bangkok Suvarnabhumi Airport", "DMK": "Bangkok Don Mueang Airport",
    "SIN": "Singapore Changi Airport", "KUL": "Kuala Lumpur International Airport",
    "TPE": "Taiwan Taoyuan Airport", "SGN": "Tan Son Nhat Airport", "HAN": "Noi Bai Airport",
    "MNL": "Ninoy Aquino Airport", "LHR": "London Heathrow Airport", "LGW": "London Gatwick Airport",
    "STN": "London Stansted Airport", "LTN": "London Luton Airport", "LCY": "London City Airport",
    "CDG": "Paris Charles de Gaulle Airport", "ORY": "Paris Orly Airport", "FRA": "Frankfurt Airport",
    "JFK": "New York JFK Airport", "EWR": "Newark Liberty Airport", "LGA": "New York LaGuardia Airport",
    "LAX": "Los Angeles International Airport", "SFO": "San Francisco International Airport",
    "YYZ": "Toronto Pearson Airport", "YVR": "Vancouver International Airport",
}


def build_search_queries(
    origin: ResolvedCity,
    destination: ResolvedCity,
    candidate_hubs: list[CandidateAirport],
    departure_date: date,
    max_route_queries: int,
    second_leg_day_offsets: tuple[int, ...] = (0, 1),
) -> tuple[list[FlightQuery], list[FlightQuery], list[CandidateAirport], list[str]]:
    baseline_pairs = [
        FlightQuery(origin=a.iata_code, destination=b.iata_code, departure_date=departure_date, kind="baseline")
        for a in origin.airports for b in destination.airports
    ]
    if len(baseline_pairs) > max_route_queries:
        raise ValueError("airport_matrix_too_large")
    queries = {(q.origin, q.destination, q.departure_date, q.kind, q.hub): q for q in baseline_pairs}
    included: list[CandidateAirport] = []
    excluded: list[str] = []
    for hub in candidate_hubs:
        candidates = [
            FlightQuery(origin=a.iata_code, destination=hub.iata_code, departure_date=departure_date, kind="outbound_to_hub", hub=hub.iata_code)
            for a in origin.airports
        ] + [
            FlightQuery(origin=hub.iata_code, destination=b.iata_code, departure_date=departure_date + timedelta(days=offset), kind="hub_to_destination" if offset == 0 else f"hub_to_destination_day_{offset + 1}", hub=hub.iata_code)
            for b in destination.airports for offset in second_leg_day_offsets
        ]
        new = [q for q in candidates if (q.origin, q.destination, q.departure_date, q.kind, q.hub) not in queries]
        if len(queries) + len(new) > max_route_queries:
            excluded.append(hub.iata_code)
            continue
        included.append(hub)
        for q in new:
            queries[(q.origin, q.destination, q.departure_date, q.kind, q.hub)] = q
    return baseline_pairs, list(queries.values()), included, excluded


class CityService:
    def __init__(self) -> None:
        mock_airports = {f.origin for f in MOCK_FLIGHTS} | {f.destination for f in MOCK_FLIGHTS}
        country_names = {country.country_id: country.country_name_en for country in COUNTRIES}
        self.cities = {
            seed.city_id: City(
                city_id=seed.city_id, city_name_zh=seed.zh, city_name_en=seed.en,
                country_id=seed.country_id, airport_codes=list(seed.airports),
                priority=seed.priority, enabled=True,
            ) for seed in CITY_SEEDS
        }
        self.airports: dict[str, CandidateAirport] = {}
        for seed in CITY_SEEDS:
            for index, code in enumerate(seed.airports):
                self.airports[code] = CandidateAirport(
                    iata_code=code, name=AIRPORT_NAMES[code], display_name=AIRPORT_NAMES[code].removesuffix(" Airport"),
                    city=seed.en, country=country_names[seed.country_id], is_primary=index == 0,
                    international=True, priority=index + 1, distance_to_city_km=0,
                    has_mock_flight_data=code in mock_airports,
                )

    def catalog(self) -> CityCatalog:
        return CityCatalog(
            version=CATALOG_VERSION,
            continents=sorted(CONTINENTS, key=lambda item: item.priority),
            countries=sorted(COUNTRIES, key=lambda item: (item.continent_id, item.priority)),
            cities=sorted(self.cities.values(), key=lambda item: (item.country_id, item.priority, item.city_name_en)),
        )

    def resolve(self, city_id: str, max_airports: int = 3) -> ResolvedCity:
        city = self.cities.get(city_id.strip().lower())
        if city is None or not city.enabled:
            raise ValueError("invalid_city_id")
        airports = self.sort_airports([self.airports[code] for code in city.airport_codes])[:max_airports]
        if not airports:
            raise ValueError("city_has_no_airports")
        return ResolvedCity(
            city_id=city.city_id, city_name_zh=city.city_name_zh, city_name_en=city.city_name_en,
            country_id=city.country_id, airports=airports,
        )

    def sort_airports(self, airports: list[CandidateAirport]) -> list[CandidateAirport]:
        return sorted(airports, key=lambda a: (not a.is_primary, not a.international, a.priority, a.distance_to_city_km, not a.has_mock_flight_data, a.iata_code))

    def airport_label(self, iata_code: str) -> str:
        airport = self.airports.get(iata_code)
        return f"{airport.display_name} ({iata_code})" if airport else iata_code

    def build_matrix(self, request: SearchRequest, candidate_hubs: tuple[str, ...], max_route_queries: int = MAX_ROUTE_QUERIES) -> AirportSearchMatrix:
        origin = self.resolve(request.origin_city_id, MAX_ORIGIN_AIRPORTS)
        destination = self.resolve(request.destination_city_id, MAX_DESTINATION_AIRPORTS)
        origin_codes = {airport.iata_code for airport in origin.airports}
        destination_codes = {airport.iata_code for airport in destination.airports}
        hubs = [self.airports[code] for code in candidate_hubs if code in self.airports and code not in origin_codes | destination_codes][:MAX_MATRIX_HUBS]
        baseline, plan, included, excluded = build_search_queries(
            origin, destination, hubs, request.departure_date, max_route_queries,
            (0, 1, 2) if request.max_gap_hours > 24 else (0, 1),
        )
        return AirportSearchMatrix(
            origin=origin, destination=destination, origin_airports=origin.airports,
            destination_airports=destination.airports, hubs=included, excluded_hubs=excluded,
            baseline_pairs=baseline, query_plan=plan, query_plan_truncated=bool(excluded),
            max_route_queries=max_route_queries,
        )


city_service = CityService()
