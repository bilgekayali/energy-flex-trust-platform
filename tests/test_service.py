"""Domain workflow, safety invariant, and evidence tests."""

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
from energy_flex_trust.domain import Actor, ActorRole, AssetStatus, FlexDirection
from energy_flex_trust.errors import ConflictError, ForbiddenError
from energy_flex_trust.models import Asset, AuditEvent
from energy_flex_trust.outbox import OutboxWorker
from energy_flex_trust.ports import NoopDispatchPublisher
from energy_flex_trust.schemas import (
    AssetCreate,
    DispatchCreate,
    MeterReadingCreate,
    OfferCreate,
    ReservationCreate,
)
from energy_flex_trust.service import CoordinationService


class CoordinationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        initialize_database(self.engine)
        self.session_factory = build_session_factory(self.engine)
        self.session = self.session_factory()
        self.service = CoordinationService(self.session)
        self.owner = Actor("owner-001", ActorRole.ASSET_OWNER)
        self.operator = Actor("operator-001", ActorRole.MARKET_OPERATOR)
        self.analyst = Actor("analyst-001", ActorRole.SETTLEMENT_ANALYST)
        self.auditor = Actor("auditor-001", ActorRole.AUDITOR)
        self.start = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
        self.end = self.start + timedelta(hours=1)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def create_asset_and_offer(self):
        asset = self.service.register_asset(
            AssetCreate(
                external_id="BATTERY-GB-001",
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
        return asset, offer

    def create_dispatched_reservation(self):
        asset, offer = self.create_asset_and_offer()
        reservation = self.service.reserve_offer(
            offer.id,
            ReservationCreate(quantity_kw=Decimal("50")),
            self.operator,
            "reserve-001",
        )
        dispatch = self.service.issue_dispatch(
            reservation.id,
            DispatchCreate(
                target_kw=Decimal("40"),
                starts_at=self.start,
                ends_at=self.end,
            ),
            self.operator,
            "dispatch-001",
        )
        result = OutboxWorker(
            self.session_factory,
            NoopDispatchPublisher(),
        ).run_once(limit=1)
        self.assertEqual(result.published, 1)
        self.session.refresh(reservation)
        self.session.refresh(dispatch)
        self.session.commit()
        return asset, offer, reservation, dispatch

    def test_complete_workflow_produces_verifiable_evidence(self) -> None:
        asset, _offer, reservation, dispatch = self.create_dispatched_reservation()
        reading = self.service.record_meter_reading(
            MeterReadingCreate(
                asset_id=asset.id,
                interval_start=self.start,
                interval_end=self.end,
                energy_kwh=Decimal("24.5"),
                source="synthetic-meter-001",
            ),
            self.owner,
        )
        duplicate = self.service.record_meter_reading(
            MeterReadingCreate(
                asset_id=asset.id,
                interval_start=self.start,
                interval_end=self.end,
                energy_kwh=Decimal("24.5"),
                source="synthetic-meter-001",
            ),
            self.owner,
        )
        self.assertEqual(duplicate.id, reading.id)

        settlement = self.service.settle_reservation(
            reservation.id,
            self.analyst,
            "settle-001",
        )
        self.assertEqual(settlement.delivered_kwh, Decimal("24.500000"))
        self.assertEqual(settlement.amount, Decimal("12.250000"))
        self.assertEqual(dispatch.adapter_reference, f"noop:{dispatch.id}")

        evidence = self.service.settlement_evidence(settlement.id, self.auditor)
        self.assertTrue(evidence["hash_valid"])
        self.assertEqual(
            evidence["manifest"]["meter_reading_ids"],
            [reading.id],
        )
        verification = self.service.audit_verification(self.auditor)
        self.assertTrue(verification.valid)
        self.assertEqual(verification.event_count, 7)

    def test_reservation_idempotency_returns_same_resource(self) -> None:
        _asset, offer = self.create_asset_and_offer()
        command = ReservationCreate(quantity_kw=Decimal("50"))
        first = self.service.reserve_offer(
            offer.id,
            command,
            self.operator,
            "reserve-same",
        )
        second = self.service.reserve_offer(
            offer.id,
            command,
            self.operator,
            "reserve-same",
        )
        self.assertEqual(first.id, second.id)

    def test_idempotency_key_reuse_with_changed_payload_is_rejected(self) -> None:
        _asset, offer = self.create_asset_and_offer()
        self.service.reserve_offer(
            offer.id,
            ReservationCreate(quantity_kw=Decimal("40")),
            self.operator,
            "reserve-conflict",
        )
        with self.assertRaisesRegex(ConflictError, "different request"):
            self.service.reserve_offer(
                offer.id,
                ReservationCreate(quantity_kw=Decimal("41")),
                self.operator,
                "reserve-conflict",
            )

    def test_settlement_enforces_separation_of_duties(self) -> None:
        asset, _offer, reservation, _dispatch = self.create_dispatched_reservation()
        self.service.record_meter_reading(
            MeterReadingCreate(
                asset_id=asset.id,
                interval_start=self.start,
                interval_end=self.end,
                energy_kwh=Decimal("20"),
                source="synthetic-meter-002",
            ),
            self.owner,
        )
        same_identity_as_operator = Actor(
            self.operator.actor_id,
            ActorRole.SETTLEMENT_ANALYST,
        )
        with self.assertRaisesRegex(ForbiddenError, "separate"):
            self.service.settle_reservation(
                reservation.id,
                same_identity_as_operator,
                "settle-sod",
            )

    def test_suspended_asset_cannot_offer_capacity(self) -> None:
        asset = self.service.register_asset(
            AssetCreate(
                external_id="BATTERY-GB-002",
                owner_id=self.owner.actor_id,
                asset_type="battery",
                capacity_kw=Decimal("100"),
                location_code="GB-MAN",
            ),
            self.owner,
        )
        with self.session.begin():
            stored = self.session.get(Asset, asset.id)
            assert stored is not None
            stored.status = AssetStatus.SUSPENDED.value

        with self.assertRaisesRegex(ConflictError, "suspended"):
            self.service.create_offer(
                OfferCreate(
                    asset_id=asset.id,
                    window_start=self.start,
                    window_end=self.end,
                    direction="decrease",
                    quantity_kw=Decimal("10"),
                    price_per_kwh=Decimal("0.25"),
                ),
                self.owner,
            )

    def test_audit_chain_detects_payload_tampering(self) -> None:
        self.create_asset_and_offer()
        self.assertTrue(self.service.audit_verification(self.auditor).valid)
        self.session.rollback()

        with self.session.begin():
            event = self.session.scalar(
                select(AuditEvent).order_by(AuditEvent.sequence.asc()).limit(1)
            )
            assert event is not None
            event.payload = {"capacity_kw": "999999"}

        verification = self.service.audit_verification(self.auditor)
        self.assertFalse(verification.valid)
        self.assertEqual(verification.broken_sequence, 1)


if __name__ == "__main__":
    unittest.main()
