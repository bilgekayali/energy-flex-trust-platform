"""Relational persistence models for the coordination workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(100), index=True)
    asset_type: Mapped[str] = mapped_column(String(40))
    capacity_kw: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    location_code: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class FlexOffer(Base):
    __tablename__ = "flex_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), index=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    direction: Mapped[str] = mapped_column(String(20))
    quantity_kw: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    offer_id: Mapped[str] = mapped_column(
        ForeignKey("flex_offers.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    quantity_kw: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    status: Mapped[str] = mapped_column(String(30), default="reserved")
    requested_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    target_kw: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="issued")
    issued_by: Mapped[str] = mapped_column(String(100))
    adapter_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_meter_reading_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), index=True
    )
    interval_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    source: Mapped[str] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    recorded_by: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reservation_id: Mapped[str] = mapped_column(
        ForeignKey("reservations.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    delivered_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    evidence_manifest: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence_hash: Mapped[str] = mapped_column(String(64), index=True)
    settled_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=new_id
    )
    aggregate_type: Mapped[str] = mapped_column(String(60), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_id: Mapped[str] = mapped_column(String(100), index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("operation", "key", name="uq_idempotency_operation_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    operation: Mapped[str] = mapped_column(String(80), index=True)
    key: Mapped[str] = mapped_column(String(200), index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str] = mapped_column(String(36))
    response_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class OutboxMessage(Base):
    """Durable outbound work committed atomically with domain state."""

    __tablename__ = "outbox_messages"
    __table_args__ = (
        UniqueConstraint(
            "topic",
            "idempotency_key",
            name="uq_outbox_topic_idempotency_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adapter_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
