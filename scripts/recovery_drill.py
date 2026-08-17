"""Seed and verify a recovery fixture around a PostgreSQL dump/restore drill."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from energy_flex_trust.database import (
    build_engine,
    build_session_factory,
    initialize_database,
)
from energy_flex_trust.domain import Actor, ActorRole, FlexDirection
from energy_flex_trust.models import OutboxMessage, Settlement
from energy_flex_trust.outbox import OutboxStatus, OutboxWorker
from energy_flex_trust.ports import NoopDispatchPublisher
from energy_flex_trust.schemas import (
    AssetCreate,
    DispatchCreate,
    MeterReadingCreate,
    OfferCreate,
    ReservationCreate,
)
from energy_flex_trust.service import CoordinationService

FIXTURE_VERSION = "energy-flex-recovery-fixture.v1"


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required for the recovery drill.")
    if not value.startswith("postgresql+"):
        raise RuntimeError("The recovery drill requires an explicit PostgreSQL URL.")
    return value


def _actors() -> tuple[Actor, Actor, Actor, Actor]:
    return (
        Actor("recovery-owner", ActorRole.ASSET_OWNER),
        Actor("recovery-operator", ActorRole.MARKET_OPERATOR),
        Actor("recovery-analyst", ActorRole.SETTLEMENT_ANALYST),
        Actor("recovery-auditor", ActorRole.AUDITOR),
    )


def seed_fixture() -> dict[str, object]:
    engine = build_engine(_database_url())
    initialize_database(engine, managed=True)
    factory = build_session_factory(engine)
    owner, operator, analyst, auditor = _actors()
    start = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)

    try:
        with factory() as session:
            service = CoordinationService(session)
            asset = service.register_asset(
                AssetCreate(
                    external_id="RECOVERY-BATTERY-001",
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
                "recovery-reservation-001",
            )
            dispatch = service.issue_dispatch(
                reservation.id,
                DispatchCreate(
                    target_kw=Decimal("40"),
                    starts_at=start,
                    ends_at=end,
                ),
                operator,
                "recovery-dispatch-001",
            )
            asset_id = asset.id
            reservation_id = reservation.id
            dispatch_id = dispatch.id

        result = OutboxWorker(
            factory,
            NoopDispatchPublisher(),
            worker_id="recovery-drill-worker",
        ).run_once(limit=10)
        if result.published != 1 or result.dead != 0:
            raise RuntimeError(
                "Recovery fixture dispatch did not publish exactly once."
            )

        with factory() as session:
            service = CoordinationService(session)
            service.record_meter_reading(
                MeterReadingCreate(
                    asset_id=asset_id,
                    interval_start=start,
                    interval_end=end,
                    energy_kwh=Decimal("24.5"),
                    source="recovery-synthetic-meter",
                ),
                owner,
            )
            settlement = service.settle_reservation(
                reservation_id,
                analyst,
                "recovery-settlement-001",
            )
            evidence = service.settlement_evidence(settlement.id, auditor)
            verification = service.audit_verification(auditor)
            published = session.scalar(
                select(func.count(OutboxMessage.id)).where(
                    OutboxMessage.status == OutboxStatus.PUBLISHED.value
                )
            ) or 0
            if not evidence["hash_valid"] or not verification.valid:
                raise RuntimeError("Seeded recovery evidence is not internally valid.")
            if published != 1:
                raise RuntimeError("Seeded recovery outbox state is unexpected.")

            return {
                "fixture_version": FIXTURE_VERSION,
                "asset_id": asset_id,
                "reservation_id": reservation_id,
                "dispatch_id": dispatch_id,
                "settlement_id": settlement.id,
                "settlement_amount": format(settlement.amount, "f"),
                "evidence_hash": str(evidence["evidence_hash"]),
                "audit_event_count": verification.event_count,
                "audit_head_hash": verification.head_hash,
                "published_outbox_count": int(published),
            }
    finally:
        engine.dispose()


def verify_fixture(expected: dict[str, object]) -> None:
    if expected.get("fixture_version") != FIXTURE_VERSION:
        raise RuntimeError("Unsupported recovery fixture version.")

    engine = build_engine(_database_url())
    initialize_database(engine, managed=True)
    factory = build_session_factory(engine)
    _owner, _operator, _analyst, auditor = _actors()

    try:
        with factory() as session:
            settlement_id = str(expected["settlement_id"])
            settlement = session.get(Settlement, settlement_id)
            if settlement is None:
                raise RuntimeError("Restored settlement is missing.")

            service = CoordinationService(session)
            evidence = service.settlement_evidence(settlement_id, auditor)
            verification = service.audit_verification(auditor)
            published = session.scalar(
                select(func.count(OutboxMessage.id)).where(
                    OutboxMessage.status == OutboxStatus.PUBLISHED.value
                )
            ) or 0

            observed = {
                "settlement_amount": format(settlement.amount, "f"),
                "evidence_hash": str(evidence["evidence_hash"]),
                "audit_event_count": verification.event_count,
                "audit_head_hash": verification.head_hash,
                "published_outbox_count": int(published),
            }
            for key, value in observed.items():
                if value != expected.get(key):
                    raise RuntimeError(
                        f"Recovery verification mismatch for {key}: "
                        f"expected {expected.get(key)!r}, observed {value!r}."
                    )
            if not evidence["hash_valid"] or not verification.valid:
                raise RuntimeError("Restored evidence or audit chain is invalid.")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed")
    seed.add_argument("--output", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--input", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "seed":
        payload = seed_fixture()
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return

    expected = json.loads(args.input.read_text(encoding="utf-8"))
    verify_fixture(expected)


if __name__ == "__main__":
    main()
