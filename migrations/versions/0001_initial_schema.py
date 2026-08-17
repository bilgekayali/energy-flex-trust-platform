"""Initial v0.1 coordination schema.

Revision ID: 0001_initial_schema
Revises: none
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("owner_id", sa.String(length=100), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("capacity_kw", sa.Numeric(18, 6), nullable=False),
        sa.Column("location_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_external_id", "assets", ["external_id"], unique=True)
    op.create_index("ix_assets_owner_id", "assets", ["owner_id"], unique=False)

    op.create_table(
        "flex_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("quantity_kw", sa.Numeric(18, 6), nullable=False),
        sa.Column("price_per_kwh", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_flex_offers_asset_id",
        "flex_offers",
        ["asset_id"],
        unique=False,
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_kw", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["flex_offers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reservations_offer_id",
        "reservations",
        ["offer_id"],
        unique=True,
    )

    op.create_table(
        "dispatches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reservation_id", sa.String(length=36), nullable=False),
        sa.Column("target_kw", sa.Numeric(18, 6), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("issued_by", sa.String(length=100), nullable=False),
        sa.Column("adapter_reference", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dispatches_reservation_id",
        "dispatches",
        ["reservation_id"],
        unique=True,
    )

    op.create_table(
        "meter_readings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("interval_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("energy_kwh", sa.Numeric(18, 6), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("recorded_by", sa.String(length=100), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_meter_reading_fingerprint"),
    )
    op.create_index(
        "ix_meter_readings_asset_id",
        "meter_readings",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_meter_readings_fingerprint",
        "meter_readings",
        ["fingerprint"],
        unique=False,
    )

    op.create_table(
        "settlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reservation_id", sa.String(length=36), nullable=False),
        sa.Column("delivered_kwh", sa.Numeric(18, 6), nullable=False),
        sa.Column("price_per_kwh", sa.Numeric(18, 6), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("evidence_manifest", sa.JSON(), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("settled_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["reservations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_settlements_reservation_id",
        "settlements",
        ["reservation_id"],
        unique=True,
    )
    op.create_index(
        "ix_settlements_evidence_hash",
        "settlements",
        ["evidence_hash"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("sequence", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence"),
        sa.UniqueConstraint("event_hash"),
    )
    op.create_index(
        "ix_audit_events_event_id",
        "audit_events",
        ["event_id"],
        unique=True,
    )
    for column in (
        "aggregate_type",
        "aggregate_id",
        "event_type",
        "actor_id",
        "correlation_id",
    ):
        op.create_index(
            f"ix_audit_events_{column}",
            "audit_events",
            [column],
            unique=False,
        )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=60), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("response_snapshot", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "operation",
            "key",
            name="uq_idempotency_operation_key",
        ),
    )
    op.create_index(
        "ix_idempotency_records_operation",
        "idempotency_records",
        ["operation"],
        unique=False,
    )
    op.create_index(
        "ix_idempotency_records_key",
        "idempotency_records",
        ["key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_key", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_operation", table_name="idempotency_records")
    op.drop_table("idempotency_records")

    for column in (
        "correlation_id",
        "actor_id",
        "event_type",
        "aggregate_id",
        "aggregate_type",
    ):
        op.drop_index(f"ix_audit_events_{column}", table_name="audit_events")
    op.drop_index("ix_audit_events_event_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_settlements_evidence_hash", table_name="settlements")
    op.drop_index("ix_settlements_reservation_id", table_name="settlements")
    op.drop_table("settlements")

    op.drop_index("ix_meter_readings_fingerprint", table_name="meter_readings")
    op.drop_index("ix_meter_readings_asset_id", table_name="meter_readings")
    op.drop_table("meter_readings")

    op.drop_index("ix_dispatches_reservation_id", table_name="dispatches")
    op.drop_table("dispatches")

    op.drop_index("ix_reservations_offer_id", table_name="reservations")
    op.drop_table("reservations")

    op.drop_index("ix_flex_offers_asset_id", table_name="flex_offers")
    op.drop_table("flex_offers")

    op.drop_index("ix_assets_owner_id", table_name="assets")
    op.drop_index("ix_assets_external_id", table_name="assets")
    op.drop_table("assets")
