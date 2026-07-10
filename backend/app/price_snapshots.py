from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from app.models import NormalizedFlightOffer, PriceSnapshot, SearchRequest


CREATE_PRICE_SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS price_snapshots (
    id TEXT PRIMARY KEY,
    search_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    supplier TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_date DATE NOT NULL,
    passengers INTEGER NOT NULL,
    cabin TEXT NOT NULL,
    price_amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    last_checked_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verification_status TEXT NOT NULL,
    cache_key TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_price_snapshots_offer_checked
    ON price_snapshots (supplier, offer_id, last_checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_price_snapshots_route_date
    ON price_snapshots (origin, destination, departure_date, cabin, currency);
""".strip()


def build_price_snapshot(
    *,
    search_id: str,
    request: SearchRequest,
    offer: NormalizedFlightOffer,
    created_at: datetime,
    cache_key: str | None = None,
) -> PriceSnapshot:
    return PriceSnapshot(
        id=str(uuid4()),
        search_id=search_id,
        offer_id=offer.id,
        supplier=offer.supplier,
        origin=offer.origin,
        destination=offer.destination,
        departure_date=request.departure_date,
        passengers=request.passengers,
        cabin=request.cabin,
        price_amount=offer.price_amount,
        currency=offer.currency,
        last_checked_at=offer.last_checked_at,
        expires_at=offer.expires_at,
        verification_status="verified" if offer.expires_at > created_at else "expired",
        cache_key=cache_key,
        created_at=created_at,
    )


@dataclass
class PriceSnapshotRecorder:
    """Interface-shaped in-memory recorder; replace with a DB writer when Postgres is introduced."""

    snapshots: list[PriceSnapshot] = field(default_factory=list)

    def record_offers(
        self,
        *,
        search_id: str,
        request: SearchRequest,
        offers: list[NormalizedFlightOffer],
        created_at: datetime,
    ) -> list[PriceSnapshot]:
        unique: dict[tuple[str, str], NormalizedFlightOffer] = {}
        for offer in offers:
            unique.setdefault((offer.supplier.value, offer.id), offer)
        snapshots = [
            build_price_snapshot(
                search_id=search_id,
                request=request,
                offer=offer,
                created_at=created_at,
            )
            for offer in unique.values()
        ]
        self.snapshots.extend(snapshots)
        return snapshots


def price_snapshot_columns() -> tuple[str, ...]:
    return (
        "id",
        "search_id",
        "offer_id",
        "supplier",
        "origin",
        "destination",
        "departure_date",
        "passengers",
        "cabin",
        "price_amount",
        "currency",
        "last_checked_at",
        "expires_at",
        "verification_status",
        "cache_key",
        "created_at",
    )
