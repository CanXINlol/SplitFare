from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AirportGeo:
    latitude: float
    longitude: float


# Single authoritative coordinate source for route discovery. Coordinates are
# rounded airport reference points and are used only for great-circle detour,
# never for flight duration or schedule claims.
AIRPORT_GEO: dict[str, AirportGeo] = {
    "MEL": AirportGeo(-37.6690, 144.8410), "AVV": AirportGeo(-38.0394, 144.4694),
    "SYD": AirportGeo(-33.9399, 151.1753), "BNE": AirportGeo(-27.3842, 153.1175),
    "PER": AirportGeo(-31.9403, 115.9672), "ADL": AirportGeo(-34.9450, 138.5306),
    "PVG": AirportGeo(31.1443, 121.8083), "SHA": AirportGeo(31.1979, 121.3363),
    "PEK": AirportGeo(40.0799, 116.6031), "PKX": AirportGeo(39.5098, 116.4105),
    "CAN": AirportGeo(23.3924, 113.2988), "SZX": AirportGeo(22.6393, 113.8107),
    "HKG": AirportGeo(22.3080, 113.9185), "TPE": AirportGeo(25.0797, 121.2342),
    "BKK": AirportGeo(13.6900, 100.7501), "DMK": AirportGeo(13.9126, 100.6068),
    "SIN": AirportGeo(1.3644, 103.9915), "KUL": AirportGeo(2.7456, 101.7099),
    "ICN": AirportGeo(37.4602, 126.4407), "GMP": AirportGeo(37.5583, 126.7906),
    "HND": AirportGeo(35.5494, 139.7798), "NRT": AirportGeo(35.7720, 140.3929),
    "KIX": AirportGeo(34.4347, 135.2440), "MNL": AirportGeo(14.5086, 121.0198),
    "SGN": AirportGeo(10.8188, 106.6520), "HAN": AirportGeo(21.2212, 105.8072),
    "LHR": AirportGeo(51.4700, -0.4543), "LGW": AirportGeo(51.1537, -0.1821),
    "STN": AirportGeo(51.8850, 0.2350), "CDG": AirportGeo(49.0097, 2.5479),
    "ORY": AirportGeo(48.7262, 2.3652), "FRA": AirportGeo(50.0379, 8.5622),
    "JFK": AirportGeo(40.6413, -73.7781), "EWR": AirportGeo(40.6895, -74.1745),
    "LGA": AirportGeo(40.7769, -73.8740), "LAX": AirportGeo(33.9416, -118.4085),
    "SFO": AirportGeo(37.6213, -122.3790), "YVR": AirportGeo(49.1967, -123.1815),
    "YYZ": AirportGeo(43.6777, -79.6248),
}
