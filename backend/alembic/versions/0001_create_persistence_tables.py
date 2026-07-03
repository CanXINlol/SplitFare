"""create persistence tables

Revision ID: 0001_create_persistence_tables
Revises:
Create Date: 2026-07-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_persistence_tables"
down_revision = None
branch_labels = None
depends_on = None


def jsonb_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "airports",
        sa.Column("iata_code", sa.String(length=3), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=64), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("cache_policy", jsonb_type(), nullable=False),
        sa.Column("allows_cache", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "searches",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("origin", sa.String(length=3), nullable=False),
        sa.Column("destination", sa.String(length=3), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("min_gap_minutes", sa.Integer(), nullable=False),
        sa.Column("max_gap_minutes", sa.Integer(), nullable=False),
        sa.Column("passengers", sa.Integer(), nullable=False),
        sa.Column("cabin", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("sort", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("candidate_hubs", jsonb_type(), nullable=True),
        sa.Column("errors", jsonb_type(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("search_id", sa.String(length=64), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offer_id", sa.String(length=160), nullable=False),
        sa.Column("supplier", sa.String(length=64), sa.ForeignKey("suppliers.name"), nullable=False),
        sa.Column("origin", sa.String(length=3), nullable=False),
        sa.Column("destination", sa.String(length=3), nullable=False),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("departure_date", sa.Date(), nullable=False),
        sa.Column("passengers", sa.Integer(), nullable=False),
        sa.Column("cabin", sa.String(length=32), nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("baggage_included", sa.Boolean(), nullable=True),
        sa.Column("booking_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", jsonb_type(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_price_snapshots_offer_checked",
        "price_snapshots",
        ["supplier", "offer_id", "last_checked_at"],
    )
    op.create_index(
        "idx_price_snapshots_route_date",
        "price_snapshots",
        ["origin", "destination", "departure_date", "cabin", "currency"],
    )
    op.create_table(
        "itineraries",
        sa.Column("id", sa.String(length=512), primary_key=True),
        sa.Column("search_id", sa.String(length=64), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("layover_airport", sa.String(length=3), nullable=True),
        sa.Column("layover_departure_airport", sa.String(length=3), nullable=True),
        sa.Column("layover_gap_minutes", sa.Integer(), nullable=True),
        sa.Column("requires_ground_transfer", sa.Boolean(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("savings_vs_baseline", sa.Float(), nullable=True),
        sa.Column("value_score", sa.Float(), nullable=False),
        sa.Column("warnings", jsonb_type(), nullable=False),
        sa.Column("suppliers", jsonb_type(), nullable=False),
        sa.Column("offer_ids", jsonb_type(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "itinerary_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("itinerary_id", sa.String(length=512), sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("search_id", sa.String(length=64), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offer_id", sa.String(length=160), nullable=True),
        sa.Column("segment_id", sa.String(length=160), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=3), nullable=False),
        sa.Column("destination", sa.String(length=3), nullable=False),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("airline", sa.String(length=16), nullable=False),
        sa.Column("operating_airline", sa.String(length=16), nullable=False),
        sa.Column("flight_number", sa.String(length=16), nullable=False),
        sa.Column("supplier", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("itinerary_id", "sequence", name="uq_itinerary_segment_sequence"),
    )
    op.create_table(
        "search_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("search_id", sa.String(length=64), sa.ForeignKey("searches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload", jsonb_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("search_events")
    op.drop_table("itinerary_segments")
    op.drop_table("itineraries")
    op.drop_index("idx_price_snapshots_route_date", table_name="price_snapshots")
    op.drop_index("idx_price_snapshots_offer_checked", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_table("searches")
    op.drop_table("suppliers")
    op.drop_table("airports")
