"""Controlled terminal outbox re-drive tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from energy_flex_trust.database import (
    build_engine,
    build_session_factory,
    initialize_database,
)
from energy_flex_trust.domain import (
    Actor,
    ActorRole,
    DispatchStatus,
    FlexDirection,
    ReservationStatus,
)
from energy_flex_trust.errors import ForbiddenError
from energy_flex_trust.models import Dispatch, OutboxMessage, Reservation
from energy_flex_trust.outbox import OutboxStatus, OutboxWorker
from energy_flex_trust.ports import (
    FaultInjectingDispatchPublisher,
    NoopDispatchPublisher,
)
from energy_flex_trust.redrive import authorize_dead_dispatch_redrive
from energy_flex_trust.schemas import (
    AssetCreate,
    DispatchCreate,
    OfferCreate,
    ReservationCreate,
)
from energy_flex_trust.service import CoordinationService


def _dead_dispatch():
    engine = build_engine("sqlite+pysqlite:///:memory:")
    initialize_database(engine)
    factory = build_session_factory(engine)
    owner = Actor("owner-redrive", ActorRole.ASSET_OWNER)
    operator = Actor("operator-redrive", ActorRole.MARKET_OPERATOR)
    start = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)

    with factory() as session:
        service = CoordinationService(session)
        asset = service.register_asset(
            AssetCreate(
                external_id="REDRIVE-BATTERY-001",
                owner_id=owner.actor_id,
                asset_type="battery",
                capacity_kw=Decimal("100"),
                location_code="GB-LON",
            ),
            owner,
        )
        offer = service.create_offer(
            OfferCreate(
                asset_id=asset.id,
                window_start=start,
                window_end=end,
                direction=FlexDirection.DECREASE,
                quantity_kw=Decimal("80"),
                price_per_kwh=Decimal("0.50"),
            ),
            owner,
        )
        reservation = service.reserve_offer(
            offer.id,
            ReservationCreate(quantity_kw=Decimal("50")),
            operator,
            "redrive-reservation-001",
        )
        dispatch = service.issue_dispatch(
            reservation.id,
            DispatchCreate(
                target_kw=Decimal("40"),
                starts_at=start,
                ends_at=end,
            ),
            operator,
            "redrive-dispatch-001",
        )
        dispatch_id = dispatch.id
        reservation_id = reservation.id

    publisher = FaultInjectingDispatchPublisher(
        NoopDispatchPublisher(),
        failures_before_success=10,
    )
    result = OutboxWorker(
        factory,
        publisher,
        max_attempts=1,
        worker_id="terminal-failure-worker",
    ).run_once(limit=1)
    assert result.dead == 1

    with factory() as session:
        message = session.scalar(
            select(OutboxMessage).where(OutboxMessage.aggregate_id == dispatch_id)
        )
        assert message is not None
        message_id = message.id

    return engine, factory, dispatch_id, reservation_id, message_id


def test_recovery_operator_can_rearm_terminal_dispatch() -> None:
    engine, factory, dispatch_id, reservation_id, message_id = _dead_dispatch()
    recovery = Actor("recovery-001", ActorRole.RECOVERY_OPERATOR)
    try:
        with factory() as session:
            result = authorize_dead_dispatch_redrive(
                session,
                actor=recovery,
                message_id=message_id,
                dispatch_id=dispatch_id,
                reason="Reviewed destination outage and approved controlled retry.",
            )
            assert result.status == OutboxStatus.PENDING.value
            assert result.previous_attempts == 1
            assert result.idempotency_key == "redrive-dispatch-001"

        with factory() as session:
            message = session.get(OutboxMessage, message_id)
            dispatch = session.get(Dispatch, dispatch_id)
            reservation = session.get(Reservation, reservation_id)
            assert message is not None
            assert dispatch is not None
            assert reservation is not None
            assert message.status == OutboxStatus.PENDING.value
            assert message.attempts == 0
            assert message.last_error is None
            assert dispatch.status == DispatchStatus.QUEUED.value
            assert reservation.status == ReservationStatus.DISPATCH_PENDING.value

        delivery = OutboxWorker(
            factory,
            NoopDispatchPublisher(),
            worker_id="post-redrive-worker",
        ).run_once(limit=1)
        assert delivery.published == 1

        with factory() as session:
            message = session.get(OutboxMessage, message_id)
            dispatch = session.get(Dispatch, dispatch_id)
            reservation = session.get(Reservation, reservation_id)
            assert message is not None
            assert dispatch is not None
            assert reservation is not None
            assert message.status == OutboxStatus.PUBLISHED.value
            assert dispatch.status == DispatchStatus.ISSUED.value
            assert reservation.status == ReservationStatus.DISPATCHED.value
            verification = CoordinationService(session).audit_verification(
                Actor("auditor-redrive", ActorRole.AUDITOR)
            )
            assert verification.valid
    finally:
        engine.dispose()


def test_non_recovery_role_cannot_rearm_terminal_dispatch() -> None:
    engine, factory, dispatch_id, _reservation_id, message_id = _dead_dispatch()
    try:
        with factory() as session:
            with pytest.raises(ForbiddenError):
                authorize_dead_dispatch_redrive(
                    session,
                    actor=Actor("operator-redrive", ActorRole.MARKET_OPERATOR),
                    message_id=message_id,
                    dispatch_id=dispatch_id,
                    reason="Attempted retry without dedicated recovery authority.",
                )
    finally:
        engine.dispose()
