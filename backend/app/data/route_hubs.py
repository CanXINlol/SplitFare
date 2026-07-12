from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HubConfig:
    hub_city_id: str
    airport_codes: tuple[str, ...]
    region: str
    priority: int
    international_connectivity_score: int
    cross_airport_risk: bool
    overnight_suitability: str
    enabled: bool = True


HUBS = (
    HubConfig("city:singapore-sg", ("SIN",), "southeast-asia", 1, 96, False, "good"),
    HubConfig("city:bangkok-th", ("BKK", "DMK"), "southeast-asia", 2, 90, True, "good"),
    HubConfig("city:kuala-lumpur-my", ("KUL",), "southeast-asia", 3, 88, False, "good"),
    HubConfig("city:hong-kong-cn", ("HKG",), "east-asia", 1, 95, False, "good"),
    HubConfig("city:taipei-tw", ("TPE",), "east-asia", 2, 89, False, "good"),
    HubConfig("city:seoul-kr", ("ICN", "GMP"), "east-asia", 3, 92, True, "good"),
    HubConfig("city:tokyo-jp", ("HND", "NRT"), "east-asia", 4, 96, True, "limited"),
    HubConfig("city:guangzhou-cn", ("CAN",), "east-asia", 5, 86, False, "good"),
    HubConfig("city:vancouver-ca", ("YVR",), "north-america", 1, 88, False, "good"),
    HubConfig("city:san-francisco-us", ("SFO",), "north-america", 2, 92, False, "good"),
    HubConfig("city:los-angeles-us", ("LAX",), "north-america", 3, 94, False, "good"),
    HubConfig("city:frankfurt-de", ("FRA",), "europe", 1, 94, False, "good"),
)


REGIONAL_HUBS: dict[tuple[str, str], tuple[str, ...]] = {
    ("oceania", "asia"): ("SIN", "BKK", "KUL", "HKG", "TPE", "ICN", "NRT", "CAN"),
    ("oceania", "europe"): ("SIN", "KUL", "BKK", "HKG"),
    ("europe", "asia"): ("FRA", "HKG", "ICN", "SIN", "BKK"),
    ("north-america", "asia"): ("YVR", "SFO", "LAX", "ICN", "TPE", "HKG"),
    ("asia", "oceania"): ("SIN", "BKK", "KUL", "HKG", "TPE"),
    ("asia", "europe"): ("HKG", "SIN", "BKK", "FRA"),
    ("asia", "north-america"): ("NRT", "ICN", "TPE", "YVR", "SFO"),
}
