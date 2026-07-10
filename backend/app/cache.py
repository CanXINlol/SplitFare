from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Protocol, TypeVar

from app.models import Cabin, Supplier


MOCK_FLIGHT_PRICE_TTL_SECONDS = 5 * 60
LIVE_FLIGHT_PRICE_TTL_SECONDS = 10 * 60
AIRPORT_DATA_TTL_SECONDS = 30 * 24 * 60 * 60
FLIGHT_CACHE_VERSION = "v2"

logger = logging.getLogger("splitfare.cache")

T = TypeVar("T")


class CacheCategory(str, Enum):
    mock_flight_price = "mock_flight_price"
    live_flight_price = "live_flight_price"
    airport_data = "airport_data"


@dataclass(frozen=True)
class CachePolicy:
    category: CacheCategory
    ttl_seconds: int
    enabled: bool = True
    supplier_allows_cache: bool = True

    @property
    def can_store(self) -> bool:
        return self.enabled and self.supplier_allows_cache and self.ttl_seconds > 0


class RedisLikeClient(Protocol):
    def get(self, key: str) -> bytes | str | None:
        ...

    def setex(self, key: str, ttl_seconds: int, value: str) -> Any:
        ...

    def ping(self) -> Any:
        ...


def default_supplier_cache_policy(supplier: Supplier) -> CachePolicy:
    if supplier in {Supplier.mock_sky, Supplier.demo_air, Supplier.budget_demo}:
        return CachePolicy(CacheCategory.mock_flight_price, MOCK_FLIGHT_PRICE_TTL_SECONDS)
    return CachePolicy(CacheCategory.live_flight_price, LIVE_FLIGHT_PRICE_TTL_SECONDS)


def flight_cache_key(
    supplier: Supplier,
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int,
    cabin: Cabin,
    currency: str,
    *,
    origin_city_id: str,
    destination_city_id: str,
    resolved_origin_airports: list[str],
    resolved_destination_airports: list[str],
    min_gap_hours: float,
    max_gap_hours: float,
    supplier_mode: str,
) -> str:
    dimensions = {
        "origin_city_id": origin_city_id,
        "destination_city_id": destination_city_id,
        "resolved_origin_airports": sorted(resolved_origin_airports),
        "resolved_destination_airports": sorted(resolved_destination_airports),
        "departure_date": departure_date,
        "passengers": passengers,
        "cabin": cabin.value,
        "min_gap_hours": min_gap_hours,
        "max_gap_hours": max_gap_hours,
        "currency": currency,
        "supplier_mode": supplier_mode,
    }
    fingerprint = hashlib.sha256(
        json.dumps(dimensions, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]
    return f"flight:{FLIGHT_CACHE_VERSION}:{supplier.value}:{origin}:{destination}:{fingerprint}"


class _MemoryEntry:
    def __init__(self, value: str, expires_at: datetime):
        self.value = value
        self.expires_at = expires_at


class RedisCache:
    """Small JSON Redis wrapper with a safe in-process fallback for local demo runs."""

    def __init__(
        self,
        client: RedisLikeClient | None = None,
        redis_url: str | None = None,
        enable_memory_fallback: bool = True,
    ):
        self._client = client if client is not None else self._connect(redis_url)
        self._enable_memory_fallback = enable_memory_fallback
        self._memory: dict[str, _MemoryEntry] = {}
        self._redis_available = self._probe()

    @classmethod
    def from_env(cls) -> RedisCache:
        return cls(redis_url=os.getenv("REDIS_URL"))

    def _connect(self, redis_url: str | None) -> RedisLikeClient | None:
        if not redis_url:
            return None
        try:
            import redis  # type: ignore[import-not-found]

            return redis.Redis.from_url(redis_url)
        except Exception as exception:
            logger.info("cache.redis_unavailable reason=%s", type(exception).__name__)
            return None

    def _probe(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception as exception:
            logger.info("cache.redis_unavailable reason=%s", type(exception).__name__)
            return False

    def get_json(self, key: str) -> Any | None:
        payload = self._get_raw(key)
        if payload is None:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            logger.info("cache.invalid_json key=%s", key)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True)
        stored = False
        if self._client is not None and self._redis_available:
            try:
                self._client.setex(key, ttl_seconds, payload)
                stored = True
            except Exception as exception:
                self._redis_available = False
                logger.info("cache.redis_write_failed key=%s reason=%s", key, type(exception).__name__)
        if self._enable_memory_fallback:
            self._memory[key] = _MemoryEntry(
                payload,
                datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
            )
            stored = True
        if stored:
            logger.debug("cache.store key=%s ttl=%s", key, ttl_seconds)

    def get_or_fetch(
        self,
        key: str,
        fetch: Callable[[], T],
        ttl_seconds: int,
        *,
        serialize: Callable[[T], Any] = lambda value: value,
        deserialize: Callable[[Any], T] = lambda value: value,
        enabled: bool = True,
    ) -> T:
        if enabled:
            cached = self.get_json(key)
            if cached is not None:
                logger.debug("cache.hit key=%s", key)
                try:
                    return deserialize(cached)
                except Exception as exception:
                    logger.info("cache.decode_failed key=%s reason=%s", key, type(exception).__name__)
            logger.debug("cache.miss key=%s", key)

        value = fetch()
        if enabled and ttl_seconds > 0:
            self.set_json(key, serialize(value), ttl_seconds)
        return value

    def _get_raw(self, key: str) -> str | None:
        if self._client is not None and self._redis_available:
            try:
                value = self._client.get(key)
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return value
            except Exception as exception:
                self._redis_available = False
                logger.info("cache.redis_read_failed key=%s reason=%s", key, type(exception).__name__)
        if not self._enable_memory_fallback:
            return None
        entry = self._memory.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(timezone.utc):
            self._memory.pop(key, None)
            logger.debug("cache.expired key=%s", key)
            return None
        return entry.value
