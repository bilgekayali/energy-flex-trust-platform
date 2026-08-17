"""Transactional outbox reliability and fail-closed state tests."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

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
from energy_flex_trust.errors import InvalidTransitionError
from energy_flex_trust.models import OutboxMessage
from energy_flex_trust.outbox import OutboxStatus, OutboxWorker, outbox_snapshot
from energy_flex_trust.ports import (
    FaultInjectingDispatchPublisher,
    NoopDispatchPublisher,
)
from energy_flex_trust.schemas import (
    AssetCreate,
    DispatchCreate,
    OfferCreate,
    ReservationCreate,
)
from energy_flex_trust.service import CoordinationService


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current

    def advance(self, *, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


class OutboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        initialize_database(self.engine)
        self.session_factory = build_session_factory(self.engine)
        self.session = self.session_factory()
        self.service = CoordinationService(self.session)
        self.owner = Actor("owner-outbox", ActorRole.ASSET_OWNER)
        self.operator = Actor("operator-outbox", ActorRole.MARKET_OPERATOR)
        self.analyst = Actor("analyst-outbox", ActorRole.SETTLEMENT_ANALYST)
        self.start = datetime(2026, 8, 18, 18, 0, tzinfo=UTC)
        self.end = self.start + timedelta(hours=1)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def create_queued_dispatch(self):
        asset = self.service.register_asset(
            AssetCreate(
                external_id="BATTERY-OUTBOX-001",
                owner_id=self.owner.actor_id,
                asset_type="battery",
                capacity_kw=Decimal("100"),
                location_code="GB-LON",
            ),
            self.owner,
        )
        offer = self.service.create_offer(
            OfferCreate(
                asset_id=asset.id,
                window_start=self.start,
                window_end=self.end,
                direction=FlexDirection.DECREASE,
                quantity_kw=Decimal("80"),
                price_per_kwh=Decimal("0.50"),
            ),
            self.owner,
        )
        reservation = self.service.reserve_offer(
            offer.id,
            ReservationCreate(quantity_kw=Decimal("50")),
            self.operator,
            "outbox-reserve-001",
        )
        dispatch = self.service.issue_dispatch(
            reservation.id,
            DispatchCreate(
                target_kw=Decimal("40"),
                starts_at=self.start,
                ends_at=self.end,
            ),
            self.operator,
            "outbox-dispatch-001",
        )
        return asset, reservation, dispatch

    @staticmethod
    def _clock_from(message: OutboxMessage) -> MutableClock:
        current = message.available_at
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return MutableClock(current + timedelta(milliseconds=1))

    def test_dispatch_is_queued_atomically_then_published(self) -> None:
        _asset, reservation, dispatch = self.create_queued_dispatch()
        message = self.session.scalar(select(OutboxMessage))
        assert message is not None
        self.assertEqual(dispatch.status, DispatchStatus.QUEUED.value)
        self.assertEqual(
            reservation.status,
            ReservationStatus.DISPATCH_PENDING.value,
        )
        self.assertEqual(message.status, OutboxStatus.PENDING.value)
        self.assertEqual(dispatch.adapter_reference, f"outbox:{message.id}")

        clock = self._clock_from(message)
        self.session.rollback()
        result = OutboxWorker(
            self.session_factory,
            NoopDispatchPublisher(),
            clock=clock,
        ).run_once(limit=1)
        self.assertEqual(result.published, 1)

        self.session.expire_all()
        self.assertEqual(dispatch.status, DispatchStatus.ISSUED.value)
        self.assertEqual(reservation.status, ReservationStatus.DISPATCHED.value)
        self.assertEqual(dispatch.adapter_reference, f"noop:{dispatch.id}")
        published = self.session.get(OutboxMessage, message.id)
        assert published is not None
        self.assertEqual(published.status, OutboxStatus.PUBLISHED.value)
        self.assertEqual(published.attempts, 1)

    def test_settlement_is_blocked_while_dispatch_is_pending(self) -> None:
        _asset, reservation, _dispatch = self.create_queued_dispatch()
        with self.assertRaisesRegex(InvalidTransitionError, "delivered dispatch"):
            self.service.settle_reservation(
                reservation.id,
                self.analyst,
                "settlement-before-publish",
            )

    def test_retry_backoff_is_bounded_and_eventually_succeeds(self) -> None:
        _asset, reservation, dispatch = self.create_queued_dispatch()
        message = self.session.scalar(select(OutboxMessage))
        assert message is not None
        clock = self._clock_from(message)
        self.session.rollback()
        publisher = FaultInjectingDispatchPublisher(
            NoopDispatchPublisher(),
            failures_before_success=2,
        )
        worker = OutboxWorker(
            self.session_factory,
            publisher,
            max_attempts=4,
            base_retry_seconds=1,
            max_retry_seconds=2,
            clock=clock,
        )

        first = worker.run_once(limit=1)
        self.assertEqual(first.retried, 1)
        self.assertEqual(worker.run_once(limit=1).attempted, 0)
        clock.advance(seconds=1)
        second = worker.run_once(limit=1)
        self.assertEqual(second.retried, 1)
        clock.advance(seconds=2)
        third = worker.run_once(limit=1)
        self.assertEqual(third.published, 1)
        self.assertEqual(publisher.attempts, 3)

        self.session.expire_all()
        self.assertEqual(dispatch.status, DispatchStatus.ISSUED.value)
        self.assertEqual(reservation.status, ReservationStatus.DISPATCHED.value)
        stored = self.session.get(OutboxMessage, message.id)
        assert stored is not None
        self.assertEqual(stored.attempts, 3)
        self.assertIsNone(stored.last_error)

    def test_terminal_failure_rejects_dispatch_fail_closed(self) -> None:
        _asset, reservation, dispatch = self.create_queued_dispatch()
        message = self.session.scalar(select(OutboxMessage))
        assert message is not None
        clock = self._clock_from(message)
        self.session.rollback()
        worker = OutboxWorker(
            self.session_factory,
            FaultInjectingDispatchPublisher(
                NoopDispatchPublisher(),
                failures_before_success=10,
            ),
            max_attempts=2,
            base_retry_seconds=1,
            max_retry_seconds=1,
            clock=clock,
        )

        self.assertEqual(worker.run_once(limit=1).retried, 1)
        clock.advance(seconds=1)
        self.assertEqual(worker.run_once(limit=1).dead, 1)

        self.session.expire_all()
        self.assertEqual(dispatch.status, DispatchStatus.REJECTED.value)
        self.assertEqual(reservation.status, ReservationStatus.CANCELLED.value)
        stored = self.session.get(OutboxMessage, message.id)
        assert stored is not None
        self.assertEqual(stored.status, OutboxStatus.DEAD.value)
        self.assertIn("Injected outbound failure", stored.last_error or "")

    def test_expired_processing_lease_is_recovered(self) -> None:
        _asset, reservation, dispatch = self.create_queued_dispatch()
        message = self.session.scalar(select(OutboxMessage))
        assert message is not None
        clock = self._clock_from(message)
        message.status = OutboxStatus.PROCESSING.value
        message.locked_by = "abandoned-worker"
        message.lease_expires_at = clock.current - timedelta(seconds=1)
        self.session.commit()

        result = OutboxWorker(
            self.session_factory,
            NoopDispatchPublisher(),
            clock=clock,
        ).run_once(limit=1)
        self.assertEqual(result.published, 1)
        self.session.expire_all()
        self.assertEqual(dispatch.status, DispatchStatus.ISSUED.value)
        self.assertEqual(reservation.status, ReservationStatus.DISPATCHED.value)

    def test_snapshot_exposes_backlog_without_high_cardinality_labels(self) -> None:
        self.create_queued_dispatch()
        message = self.session.scalar(select(OutboxMessage))
        assert message is not None
        clock = self._clock_from(message)
        snapshot = outbox_snapshot(self.session, now=clock.current)
        self.assertEqual(snapshot.pending, 1)
        self.assertEqual(snapshot.processing, 0)
        self.assertEqual(snapshot.dead, 0)
        self.assertEqual(snapshot.due, 1)
        self.assertIsNotNone(snapshot.oldest_pending_age_seconds)


if __name__ == "__main__":
    unittest.main()
