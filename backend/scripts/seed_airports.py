from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, init_database
from app.repositories import SearchRepository


AIRPORTS = (
    ("MEL", "Melbourne Airport", "Melbourne", "Australia", "Australia/Melbourne"),
    ("PVG", "Shanghai Pudong International Airport", "Shanghai", "China", "Asia/Shanghai"),
    ("SHA", "Shanghai Hongqiao International Airport", "Shanghai", "China", "Asia/Shanghai"),
    ("BKK", "Suvarnabhumi Airport", "Bangkok", "Thailand", "Asia/Bangkok"),
    ("DMK", "Don Mueang International Airport", "Bangkok", "Thailand", "Asia/Bangkok"),
    ("SIN", "Singapore Changi Airport", "Singapore", "Singapore", "Asia/Singapore"),
    ("KUL", "Kuala Lumpur International Airport", "Kuala Lumpur", "Malaysia", "Asia/Kuala_Lumpur"),
    ("HKG", "Hong Kong International Airport", "Hong Kong", "Hong Kong", "Asia/Hong_Kong"),
    ("TPE", "Taiwan Taoyuan International Airport", "Taipei", "Taiwan", "Asia/Taipei"),
    ("MNL", "Ninoy Aquino International Airport", "Manila", "Philippines", "Asia/Manila"),
    ("SGN", "Tan Son Nhat International Airport", "Ho Chi Minh City", "Vietnam", "Asia/Ho_Chi_Minh"),
    ("HAN", "Noi Bai International Airport", "Hanoi", "Vietnam", "Asia/Ho_Chi_Minh"),
    ("ICN", "Incheon International Airport", "Seoul", "South Korea", "Asia/Seoul"),
    ("NRT", "Narita International Airport", "Tokyo", "Japan", "Asia/Tokyo"),
    ("KIX", "Kansai International Airport", "Osaka", "Japan", "Asia/Tokyo"),
    ("CAN", "Guangzhou Baiyun International Airport", "Guangzhou", "China", "Asia/Shanghai"),
    ("SZX", "Shenzhen Bao'an International Airport", "Shenzhen", "China", "Asia/Shanghai"),
)


def main() -> None:
    init_database()
    session = SessionLocal()
    try:
        repo = SearchRepository(session)
        for iata_code, name, city, country, timezone_name in AIRPORTS:
            repo.upsert_airport(
                iata_code=iata_code,
                name=name,
                city=city,
                country=country,
                timezone_name=timezone_name,
            )
        session.commit()
        print(f"Seeded {len(AIRPORTS)} airports.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
