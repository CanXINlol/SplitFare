from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


JsonColumn = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AirportRecord(Base):
    __tablename__ = "airports"

    iata_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SupplierRecord(Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    cache_policy: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    allows_cache: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SearchRecord(Base):
    __tablename__ = "searches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_gap_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_gap_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    passengers: Mapped[int] = mapped_column(Integer, nullable=False)
    cabin: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    sort: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_hubs: Mapped[list[str] | None] = mapped_column(JsonColumn, nullable=True)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JsonColumn, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    price_snapshots: Mapped[list[PriceSnapshotRecord]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )
    itineraries: Mapped[list[ItineraryRecord]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )
    events: Mapped[list[SearchEventRecord]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class PriceSnapshotRecord(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), nullable=False)
    offer_id: Mapped[str] = mapped_column(String(160), nullable=False)
    supplier: Mapped[str] = mapped_column(ForeignKey("suppliers.name"), nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    passengers: Mapped[int] = mapped_column(Integer, nullable=False)
    cabin: Mapped[str] = mapped_column(String(32), nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    baggage_included: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    booking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    search: Mapped[SearchRecord] = relationship(back_populates="price_snapshots")


class ItineraryRecord(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(512), primary_key=True)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    layover_airport: Mapped[str | None] = mapped_column(String(3), nullable=True)
    layover_departure_airport: Mapped[str | None] = mapped_column(String(3), nullable=True)
    layover_gap_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_ground_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    savings_vs_baseline: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_score: Mapped[float] = mapped_column(Float, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JsonColumn, default=list, nullable=False)
    suppliers: Mapped[list[str]] = mapped_column(JsonColumn, default=list, nullable=False)
    offer_ids: Mapped[list[str]] = mapped_column(JsonColumn, default=list, nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    search: Mapped[SearchRecord] = relationship(back_populates="itineraries")
    segments: Mapped[list[ItinerarySegmentRecord]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItinerarySegmentRecord.sequence",
    )


class ItinerarySegmentRecord(Base):
    __tablename__ = "itinerary_segments"
    __table_args__ = (UniqueConstraint("itinerary_id", "sequence", name="uq_itinerary_segment_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    itinerary_id: Mapped[str] = mapped_column(String(512), ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), nullable=False)
    offer_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    segment_id: Mapped[str] = mapped_column(String(160), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    airline: Mapped[str] = mapped_column(String(16), nullable=False)
    operating_airline: Mapped[str] = mapped_column(String(16), nullable=False)
    flight_number: Mapped[str] = mapped_column(String(16), nullable=False)
    supplier: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    itinerary: Mapped[ItineraryRecord] = relationship(back_populates="segments")


class SearchEventRecord(Base):
    __tablename__ = "search_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[str] = mapped_column(ForeignKey("searches.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    search: Mapped[SearchRecord] = relationship(back_populates="events")
