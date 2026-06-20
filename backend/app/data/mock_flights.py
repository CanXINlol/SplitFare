from dataclasses import dataclass

from app.models import Supplier


@dataclass(frozen=True)
class MockFlight:
    id: str
    origin: str
    destination: str
    departure_hour: int
    departure_minute: int
    duration_minutes: int
    airline: str
    flight_number: str
    price: float
    supplier: Supplier
    baggage_included: bool | None = True
    protected_connection: bool = False


# Stable fixture data: prices are fictional and are never presented as live fares.
MOCK_FLIGHTS = [
    MockFlight("direct-mu", "MEL", "PVG", 11, 0, 630, "MU", "MU738", 1120, Supplier.mock_sky, True, True),
    MockFlight("direct-qf", "MEL", "PVG", 9, 20, 650, "QF", "QF129", 1260, Supplier.demo_air, True, True),
    MockFlight("direct-sha", "MEL", "SHA", 10, 5, 660, "MU", "MU740", 1160, Supplier.mock_sky, True, True),
    MockFlight("mel-bkk", "MEL", "BKK", 7, 0, 570, "TG", "TG466", 390, Supplier.mock_sky),
    MockFlight("bkk-pvg", "BKK", "PVG", 20, 30, 255, "FM", "FM854", 330, Supplier.budget_demo, False),
    MockFlight("bkk-sha", "BKK", "SHA", 22, 0, 250, "MU", "MU548", 345, Supplier.demo_air),
    MockFlight("mel-sin", "MEL", "SIN", 6, 10, 470, "SQ", "SQ238", 440, Supplier.demo_air),
    MockFlight("sin-pvg", "SIN", "PVG", 18, 20, 320, "HO", "HO1602", 315, Supplier.budget_demo),
    MockFlight("sin-sha", "SIN", "SHA", 17, 45, 325, "MU", "MU566", 350, Supplier.mock_sky),
    MockFlight("mel-kul", "MEL", "KUL", 5, 30, 500, "MH", "MH128", 360, Supplier.mock_sky, None),
    MockFlight("kul-pvg", "KUL", "PVG", 18, 0, 330, "D7", "D7330", 285, Supplier.budget_demo, False),
    MockFlight("kul-sha", "KUL", "SHA", 19, 20, 335, "FM", "FM886", 320, Supplier.budget_demo),
    MockFlight("mel-hkg", "MEL", "HKG", 8, 15, 550, "CX", "CX134", 510, Supplier.demo_air),
    MockFlight("hkg-pvg", "HKG", "PVG", 21, 0, 155, "CX", "CX360", 260, Supplier.mock_sky),
    MockFlight("hkg-sha", "HKG", "SHA", 20, 20, 150, "HX", "HX238", 245, Supplier.budget_demo),
    MockFlight("mel-tpe", "MEL", "TPE", 7, 25, 560, "CI", "CI58", 480, Supplier.mock_sky),
    MockFlight("tpe-pvg", "TPE", "PVG", 21, 30, 125, "BR", "BR712", 240, Supplier.demo_air),
    MockFlight("tpe-sha", "TPE", "SHA", 20, 45, 120, "CI", "CI201", 250, Supplier.demo_air),
    MockFlight("mel-icn", "MEL", "ICN", 9, 0, 650, "KE", "KE402", 570, Supplier.demo_air),
    MockFlight("icn-pvg", "ICN", "PVG", 23, 30, 130, "KE", "KE895", 275, Supplier.mock_sky),
    MockFlight("icn-sha", "ICN", "SHA", 22, 50, 135, "OZ", "OZ361", 270, Supplier.mock_sky),
    MockFlight("mel-nrt", "MEL", "NRT", 6, 45, 620, "JL", "JL774", 610, Supplier.demo_air),
    MockFlight("nrt-pvg", "NRT", "PVG", 21, 0, 190, "JL", "JL877", 290, Supplier.mock_sky),
    MockFlight("nrt-sha", "NRT", "SHA", 20, 30, 195, "NH", "NH969", 300, Supplier.demo_air),
    MockFlight("mel-can", "MEL", "CAN", 10, 0, 590, "CZ", "CZ344", 500, Supplier.mock_sky),
    MockFlight("can-pvg", "CAN", "PVG", 22, 30, 145, "CZ", "CZ3586", 210, Supplier.demo_air),
    MockFlight("can-sha", "CAN", "SHA", 21, 50, 140, "FM", "FM9312", 205, Supplier.budget_demo),
]
