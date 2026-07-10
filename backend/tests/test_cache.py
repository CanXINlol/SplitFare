import asyncio
import logging
from datetime import date

from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.cache import RedisCache, flight_cache_key
from app.models import Cabin, PriceStatus, SearchCacheContext, Supplier


CONTEXT = SearchCacheContext(
    originCityId="city:melbourne-au",
    destinationCityId="city:shanghai-cn",
    resolvedOriginAirports=["MEL", "AVV"],
    resolvedDestinationAirports=["PVG", "SHA"],
    minGapHours=3,
    maxGapHours=12,
    supplierMode="mock",
)


class CountingMockAdapter(MockSupplierAdapter):
    def __init__(self):
        super().__init__(Supplier.mock_sky)
        self.fetch_count = 0

    def _fetch_one_way(self, *args, **kwargs):
        self.fetch_count += 1
        return super()._fetch_one_way(*args, **kwargs)


class DownRedis:
    def ping(self):
        raise RuntimeError("redis down")

    def get(self, key: str):
        raise RuntimeError("redis down")

    def setex(self, key: str, ttl_seconds: int, value: str):
        raise RuntimeError("redis down")


def test_get_or_fetch_miss_then_hit(caplog) -> None:
    caplog.set_level(logging.DEBUG, logger="splitfare.cache")
    cache = RedisCache(enable_memory_fallback=True)
    calls = 0

    def fetch() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"value": 42}

    assert cache.get_or_fetch("demo:key", fetch, 60) == {"value": 42}
    assert cache.get_or_fetch("demo:key", fetch, 60) == {"value": 42}
    assert calls == 1
    messages = [record.message for record in caplog.records]
    assert any("cache.miss" in message for message in messages)
    assert any("cache.hit" in message for message in messages)


def test_ttl_expired_refetches() -> None:
    cache = RedisCache(enable_memory_fallback=True)
    calls = 0

    def fetch() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    cache.set_json("short:key", {"calls": 0}, ttl_seconds=-1)
    assert cache.get_or_fetch("short:key", fetch, 60) == {"calls": 1}
    assert calls == 1


def test_redis_down_does_not_block_fetch() -> None:
    cache = RedisCache(client=DownRedis(), enable_memory_fallback=False)
    assert cache.get_or_fetch("down:key", lambda: {"ok": True}, 60) == {"ok": True}


def test_second_same_route_search_hits_supplier_cache() -> None:
    adapter = CountingMockAdapter()
    orchestrator = SupplierOrchestrator([adapter], cache=RedisCache(enable_memory_fallback=True))
    query = ("MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD")

    first = asyncio.run(orchestrator.search_route(*query, CONTEXT))
    second = asyncio.run(orchestrator.search_route(*query, CONTEXT))

    assert [offer.id for offer in first.offers] == [offer.id for offer in second.offers]
    assert all(offer.price_status == PriceStatus.confirmed for offer in first.offers)
    assert all(offer.price_status == PriceStatus.cached for offer in second.offers)
    assert adapter.fetch_count == 1


def test_flight_cache_key_uses_required_shape() -> None:
    key = flight_cache_key(
        Supplier.mock_sky,
        "MEL",
        "PVG",
        "2026-08-12",
        1,
        Cabin.economy,
        "AUD",
        origin_city_id="city:melbourne-au",
        destination_city_id="city:shanghai-cn",
        resolved_origin_airports=["MEL", "AVV"],
        resolved_destination_airports=["PVG", "SHA"],
        min_gap_hours=3,
        max_gap_hours=12,
        supplier_mode="mock",
    )
    assert key.startswith("flight:v2:MockSky:MEL:PVG:")


def test_cache_key_changes_for_city_airports_gap_and_mode() -> None:
    base = dict(
        supplier=Supplier.mock_sky, origin="MEL", destination="PVG",
        departure_date="2026-08-12", passengers=1, cabin=Cabin.economy, currency="AUD",
        origin_city_id="city:melbourne-au", destination_city_id="city:shanghai-cn",
        resolved_origin_airports=["MEL", "AVV"], resolved_destination_airports=["PVG", "SHA"],
        min_gap_hours=3, max_gap_hours=12, supplier_mode="mock",
    )
    key = flight_cache_key(**base)
    assert flight_cache_key(**{**base, "resolved_destination_airports": ["PVG"]}) != key
    assert flight_cache_key(**{**base, "min_gap_hours": 4}) != key
    assert flight_cache_key(**{**base, "supplier_mode": "live"}) != key
