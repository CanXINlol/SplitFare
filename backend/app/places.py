from __future__ import annotations

from dataclasses import dataclass
from unicodedata import normalize

from app.data.mock_flights import MOCK_FLIGHTS
from app.models import (
    AirportSearchMatrix,
    CandidateAirport,
    FlightQuery,
    Place,
    PlaceAlias,
    PlaceType,
    ResolvedPlace,
    SearchRequest,
)


MAX_ORIGIN_AIRPORTS = 3
MAX_DESTINATION_AIRPORTS = 3
MAX_MATRIX_HUBS = 12


@dataclass(frozen=True)
class AirportSeed:
    code: str
    name: str
    display_name: str
    city: str
    country: str
    is_primary: bool
    international: bool
    priority: int
    distance_to_city_km: float


@dataclass(frozen=True)
class CitySeed:
    place_id: str
    name: str
    country: str
    airport_codes: tuple[str, ...]
    aliases: tuple[str, ...]
    is_major_hub: bool
    priority: int


AIRPORT_SEEDS: tuple[AirportSeed, ...] = (
    AirportSeed("MEL", "Melbourne Airport", "Melbourne", "Melbourne", "Australia", True, True, 1, 23),
    AirportSeed("AVV", "Avalon Airport", "Avalon", "Melbourne", "Australia", False, True, 4, 55),
    AirportSeed("SYD", "Sydney Kingsford Smith Airport", "Sydney", "Sydney", "Australia", True, True, 1, 8),
    AirportSeed("BNE", "Brisbane Airport", "Brisbane", "Brisbane", "Australia", True, True, 1, 17),
    AirportSeed("PER", "Perth Airport", "Perth", "Perth", "Australia", True, True, 1, 12),
    AirportSeed("ADL", "Adelaide Airport", "Adelaide", "Adelaide", "Australia", True, True, 1, 6),
    AirportSeed("PVG", "Shanghai Pudong Airport", "Shanghai Pudong", "Shanghai", "China", True, True, 1, 30),
    AirportSeed("SHA", "Shanghai Hongqiao Airport", "Shanghai Hongqiao", "Shanghai", "China", False, True, 2, 13),
    AirportSeed("PEK", "Beijing Capital Airport", "Beijing Capital", "Beijing", "China", True, True, 1, 26),
    AirportSeed("PKX", "Beijing Daxing Airport", "Beijing Daxing", "Beijing", "China", False, True, 2, 46),
    AirportSeed("CAN", "Guangzhou Baiyun Airport", "Guangzhou", "Guangzhou", "China", True, True, 1, 28),
    AirportSeed("SZX", "Shenzhen Bao'an Airport", "Shenzhen", "Shenzhen", "China", True, True, 1, 32),
    AirportSeed("NKG", "Nanjing Lukou Airport", "Nanjing", "Nanjing", "China", True, True, 1, 35),
    AirportSeed("HGH", "Hangzhou Xiaoshan Airport", "Hangzhou", "Hangzhou", "China", True, True, 1, 28),
    AirportSeed("CTU", "Chengdu Shuangliu Airport", "Chengdu Shuangliu", "Chengdu", "China", False, True, 2, 16),
    AirportSeed("TFU", "Chengdu Tianfu Airport", "Chengdu Tianfu", "Chengdu", "China", True, True, 1, 51),
    AirportSeed("HKG", "Hong Kong International Airport", "Hong Kong", "Hong Kong", "China", True, True, 1, 34),
    AirportSeed("BKK", "Bangkok Suvarnabhumi Airport", "Bangkok", "Bangkok", "Thailand", True, True, 1, 31),
    AirportSeed("DMK", "Bangkok Don Mueang Airport", "Bangkok Don Mueang", "Bangkok", "Thailand", False, True, 2, 24),
    AirportSeed("SIN", "Singapore Changi Airport", "Singapore", "Singapore", "Singapore", True, True, 1, 20),
    AirportSeed("KUL", "Kuala Lumpur International Airport", "Kuala Lumpur", "Kuala Lumpur", "Malaysia", True, True, 1, 45),
    AirportSeed("TPE", "Taiwan Taoyuan Airport", "Taipei Taoyuan", "Taipei", "Taiwan", True, True, 1, 40),
    AirportSeed("ICN", "Seoul Incheon Airport", "Seoul Incheon", "Seoul", "South Korea", True, True, 1, 49),
    AirportSeed("GMP", "Seoul Gimpo Airport", "Seoul Gimpo", "Seoul", "South Korea", False, True, 2, 16),
    AirportSeed("HND", "Tokyo Haneda Airport", "Tokyo Haneda", "Tokyo", "Japan", True, True, 1, 15),
    AirportSeed("NRT", "Tokyo Narita Airport", "Tokyo Narita", "Tokyo", "Japan", False, True, 2, 64),
    AirportSeed("KIX", "Osaka Kansai Airport", "Osaka Kansai", "Osaka", "Japan", True, True, 1, 50),
    AirportSeed("MNL", "Manila Ninoy Aquino Airport", "Manila", "Manila", "Philippines", True, True, 1, 7),
    AirportSeed("SGN", "Ho Chi Minh City Tan Son Nhat Airport", "Ho Chi Minh City", "Ho Chi Minh City", "Vietnam", True, True, 1, 7),
    AirportSeed("HAN", "Hanoi Noi Bai Airport", "Hanoi", "Hanoi", "Vietnam", True, True, 1, 27),
    AirportSeed("LHR", "London Heathrow Airport", "London Heathrow", "London", "United Kingdom", True, True, 1, 24),
    AirportSeed("LGW", "London Gatwick Airport", "London Gatwick", "London", "United Kingdom", False, True, 2, 45),
    AirportSeed("STN", "London Stansted Airport", "London Stansted", "London", "United Kingdom", False, True, 3, 64),
    AirportSeed("LTN", "London Luton Airport", "London Luton", "London", "United Kingdom", False, True, 4, 55),
    AirportSeed("LCY", "London City Airport", "London City", "London", "United Kingdom", False, True, 5, 14),
    AirportSeed("JFK", "New York JFK Airport", "New York JFK", "New York", "United States", True, True, 1, 26),
    AirportSeed("EWR", "Newark Liberty Airport", "Newark", "New York", "United States", False, True, 2, 24),
    AirportSeed("LGA", "New York LaGuardia Airport", "New York LaGuardia", "New York", "United States", False, True, 3, 14),
    AirportSeed("LAX", "Los Angeles International Airport", "Los Angeles", "Los Angeles", "United States", True, True, 1, 30),
    AirportSeed("SFO", "San Francisco International Airport", "San Francisco", "San Francisco", "United States", True, True, 1, 21),
    AirportSeed("CDG", "Paris Charles de Gaulle Airport", "Paris Charles de Gaulle", "Paris", "France", True, True, 1, 25),
    AirportSeed("ORY", "Paris Orly Airport", "Paris Orly", "Paris", "France", False, True, 2, 13),
    AirportSeed("FRA", "Frankfurt Airport", "Frankfurt", "Frankfurt", "Germany", True, True, 1, 12),
)


CITY_SEEDS: tuple[CitySeed, ...] = (
    CitySeed("city:melbourne-au", "Melbourne", "Australia", ("MEL", "AVV"), ("Melbourne", "墨尔本"), True, 1),
    CitySeed("city:sydney-au", "Sydney", "Australia", ("SYD",), ("Sydney", "悉尼"), True, 1),
    CitySeed("city:brisbane-au", "Brisbane", "Australia", ("BNE",), ("Brisbane", "布里斯班"), False, 2),
    CitySeed("city:perth-au", "Perth", "Australia", ("PER",), ("Perth", "珀斯"), False, 2),
    CitySeed("city:adelaide-au", "Adelaide", "Australia", ("ADL",), ("Adelaide", "阿德莱德"), False, 2),
    CitySeed("city:shanghai-cn", "Shanghai", "China", ("PVG", "SHA"), ("Shanghai", "上海"), True, 1),
    CitySeed("city:beijing-cn", "Beijing", "China", ("PEK", "PKX"), ("Beijing", "北京"), True, 1),
    CitySeed("city:guangzhou-cn", "Guangzhou", "China", ("CAN",), ("Guangzhou", "广州"), True, 1),
    CitySeed("city:shenzhen-cn", "Shenzhen", "China", ("SZX",), ("Shenzhen", "深圳"), True, 1),
    CitySeed("city:nanjing-cn", "Nanjing", "China", ("NKG",), ("Nanjing", "南京"), False, 2),
    CitySeed("city:hangzhou-cn", "Hangzhou", "China", ("HGH",), ("Hangzhou", "杭州"), False, 2),
    CitySeed("city:chengdu-cn", "Chengdu", "China", ("TFU", "CTU"), ("Chengdu", "成都"), False, 2),
    CitySeed("city:hong-kong-cn", "Hong Kong", "China", ("HKG",), ("Hong Kong", "香港"), True, 1),
    CitySeed("city:bangkok-th", "Bangkok", "Thailand", ("BKK", "DMK"), ("Bangkok", "曼谷"), True, 1),
    CitySeed("city:singapore-sg", "Singapore", "Singapore", ("SIN",), ("Singapore", "新加坡"), True, 1),
    CitySeed("city:kuala-lumpur-my", "Kuala Lumpur", "Malaysia", ("KUL",), ("Kuala Lumpur", "吉隆坡"), True, 1),
    CitySeed("city:taipei-tw", "Taipei", "Taiwan", ("TPE",), ("Taipei", "台北"), True, 1),
    CitySeed("city:seoul-kr", "Seoul", "South Korea", ("ICN", "GMP"), ("Seoul", "首尔"), True, 1),
    CitySeed("city:tokyo-jp", "Tokyo", "Japan", ("HND", "NRT"), ("Tokyo", "东京"), True, 1),
    CitySeed("city:osaka-jp", "Osaka", "Japan", ("KIX",), ("Osaka", "大阪"), False, 2),
    CitySeed("city:manila-ph", "Manila", "Philippines", ("MNL",), ("Manila", "马尼拉"), False, 2),
    CitySeed("city:ho-chi-minh-vn", "Ho Chi Minh City", "Vietnam", ("SGN",), ("Ho Chi Minh City", "胡志明市"), False, 2),
    CitySeed("city:hanoi-vn", "Hanoi", "Vietnam", ("HAN",), ("Hanoi", "河内"), False, 2),
    CitySeed("city:london-gb", "London", "United Kingdom", ("LHR", "LGW", "STN", "LTN", "LCY"), ("London", "伦敦"), True, 1),
    CitySeed("city:new-york-us", "New York", "United States", ("JFK", "EWR", "LGA"), ("New York", "纽约"), True, 1),
    CitySeed("city:los-angeles-us", "Los Angeles", "United States", ("LAX",), ("Los Angeles", "洛杉矶"), True, 1),
    CitySeed("city:san-francisco-us", "San Francisco", "United States", ("SFO",), ("San Francisco", "旧金山"), True, 1),
    CitySeed("city:paris-fr", "Paris", "France", ("CDG", "ORY"), ("Paris", "巴黎"), True, 1),
    CitySeed("city:frankfurt-de", "Frankfurt", "Germany", ("FRA",), ("Frankfurt", "法兰克福"), True, 1),
)


def _key(value: str) -> str:
    return normalize("NFKC", value).casefold().strip()


class PlaceService:
    def __init__(self) -> None:
        self.mock_airports = {
            flight.origin for flight in MOCK_FLIGHTS
        } | {
            flight.destination for flight in MOCK_FLIGHTS
        }
        self.airports = {
            seed.code: CandidateAirport(
                iata_code=seed.code,
                name=seed.name,
                display_name=seed.display_name,
                city=seed.city,
                country=seed.country,
                is_primary=seed.is_primary,
                international=seed.international,
                priority=seed.priority,
                distance_to_city_km=seed.distance_to_city_km,
                has_mock_flight_data=seed.code in self.mock_airports,
            )
            for seed in AIRPORT_SEEDS
        }
        self.places = self._build_places()

    def _build_places(self) -> dict[str, Place]:
        places: dict[str, Place] = {}
        for seed in CITY_SEEDS:
            places[seed.place_id] = Place(
                id=seed.place_id,
                type=PlaceType.city,
                name=seed.name,
                display_name=f"{seed.name}, {seed.country}",
                country=seed.country,
                aliases=[PlaceAlias(value=alias) for alias in seed.aliases],
                airport_codes=list(seed.airport_codes),
                is_major_hub=seed.is_major_hub,
                priority=seed.priority,
            )
        for airport in self.airports.values():
            places[f"airport:{airport.iata_code}"] = Place(
                id=f"airport:{airport.iata_code}",
                type=PlaceType.airport,
                name=airport.name,
                display_name=f"{airport.name} ({airport.iata_code})",
                country=airport.country,
                aliases=[
                    PlaceAlias(value=airport.iata_code),
                    PlaceAlias(value=airport.name),
                    PlaceAlias(value=airport.display_name),
                    PlaceAlias(value=airport.city),
                ],
                airport_codes=[airport.iata_code],
                iata_code=airport.iata_code,
                is_major_hub=airport.is_primary,
                priority=airport.priority,
            )
        return places

    def airport_label(self, iata_code: str) -> str:
        airport = self.airports.get(iata_code)
        return f"{airport.display_name} ({iata_code})" if airport else iata_code

    def search(self, query: str, limit: int = 8) -> list[Place]:
        q = _key(query)
        if not q:
            return []
        scored: list[tuple[tuple[int, int, int, int, str], Place]] = []
        for place in self.places.values():
            rank = self._match_rank(place, q)
            if rank is None:
                continue
            scored.append((
                (
                    rank,
                    0 if place.is_major_hub else 1,
                    place.priority,
                    0 if place.type == PlaceType.city else 1,
                    place.display_name,
                ),
                place,
            ))
        return [place for _, place in sorted(scored, key=lambda item: item[0])[:limit]]

    def _match_rank(self, place: Place, q: str) -> int | None:
        aliases = [place.name, place.display_name, *(alias.value for alias in place.aliases)]
        if place.iata_code and q == _key(place.iata_code):
            return 0
        if place.type in {PlaceType.city, PlaceType.metro_area} and q == _key(place.name):
            return 1
        if any(q == _key(alias) for alias in aliases):
            return 2
        if any(_key(alias).startswith(q) for alias in aliases):
            return 3
        if any(q in _key(alias) for alias in aliases):
            return 4
        return None

    def resolve(self, place_id: str, max_airports: int = 3) -> ResolvedPlace:
        normalized_id = self._normalize_place_id(place_id)
        place = self.places.get(normalized_id)
        if place is None:
            raise ValueError(f"Unknown place '{place_id}'. Choose a city or airport from the suggestions.")
        airports = [self.airports[code] for code in place.airport_codes if code in self.airports]
        if not airports:
            raise ValueError(f"Place '{place.display_name}' has no supported airports in the seed data.")
        airports = self.sort_airports(airports)[:max_airports]
        return ResolvedPlace(
            place_id=place.id,
            type=place.type,
            display_name=place.display_name,
            country=place.country,
            airports=airports,
        )

    def sort_airports(self, airports: list[CandidateAirport]) -> list[CandidateAirport]:
        return sorted(
            airports,
            key=lambda airport: (
                not airport.is_primary,
                not airport.international,
                airport.priority,
                airport.distance_to_city_km,
                not airport.has_mock_flight_data,
                airport.iata_code,
            ),
        )

    def build_matrix(self, request: SearchRequest, candidate_hubs: tuple[str, ...]) -> AirportSearchMatrix:
        origin = self.resolve(request.origin_place_id, MAX_ORIGIN_AIRPORTS)
        destination = self.resolve(request.destination_place_id, MAX_DESTINATION_AIRPORTS)
        origin_codes = {airport.iata_code for airport in origin.airports}
        destination_codes = {airport.iata_code for airport in destination.airports}
        if origin_codes & destination_codes:
            raise ValueError("Origin and destination resolve to the same airport. Choose different places.")
        hubs = [
            self.airports[code]
            for code in candidate_hubs
            if code in self.airports and code not in origin_codes and code not in destination_codes
        ][:MAX_MATRIX_HUBS]
        baseline_pairs = [
            FlightQuery(
                origin=origin_airport.iata_code,
                destination=destination_airport.iata_code,
                departure_date=request.departure_date,
                kind="baseline",
            )
            for origin_airport in origin.airports
            for destination_airport in destination.airports
        ]
        queries: dict[tuple[str, str, str, str | None], FlightQuery] = {
            (query.origin, query.destination, query.kind, query.hub): query for query in baseline_pairs
        }
        for origin_airport in origin.airports:
            for destination_airport in destination.airports:
                for hub in hubs:
                    outbound = FlightQuery(
                        origin=origin_airport.iata_code,
                        destination=hub.iata_code,
                        departure_date=request.departure_date,
                        kind="outbound_to_hub",
                        hub=hub.iata_code,
                    )
                    inbound = FlightQuery(
                        origin=hub.iata_code,
                        destination=destination_airport.iata_code,
                        departure_date=request.departure_date,
                        kind="hub_to_destination",
                        hub=hub.iata_code,
                    )
                    queries.setdefault((outbound.origin, outbound.destination, outbound.kind, outbound.hub), outbound)
                    queries.setdefault((inbound.origin, inbound.destination, inbound.kind, inbound.hub), inbound)
        return AirportSearchMatrix(
            origin=origin,
            destination=destination,
            origin_airports=origin.airports,
            destination_airports=destination.airports,
            hubs=hubs,
            baseline_pairs=baseline_pairs,
            query_plan=list(queries.values()),
        )

    def _normalize_place_id(self, place_id: str) -> str:
        stripped = place_id.strip()
        if stripped.lower().startswith("airport:"):
            return f"airport:{stripped.split(':', 1)[1].upper()}"
        return stripped.lower()


place_service = PlaceService()
