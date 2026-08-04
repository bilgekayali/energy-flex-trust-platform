"""Tamper-evident audit-chain functions.

The chain detects mutations or deletions in the ordered event stream. It is not a
digital signature and does not provide non-repudiation by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent

GENESIS_HASH = "0" * 64


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def audit_hash_material(event: AuditEvent) -> dict[str, Any]:
    occurred_at = event.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    return {
        "event_id": event.event_id,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "correlation_id": event.correlation_id,
        "payload": event.payload,
        "occurred_at": occurred_at.astimezone(UTC).isoformat(),
        "previous_hash": event.previous_hash,
    }


def calculate_event_hash(event: AuditEvent) -> str:
    return sha256_json(audit_hash_material(event))


def append_event(
    session: Session,
    *,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    actor_id: str,
    correlation_id: str,
    payload: dict[str, Any],
) -> AuditEvent:
    normalized_payload = json.loads(canonical_json(payload))
    latest = session.scalar(
        select(AuditEvent)
        .order_by(AuditEvent.sequence.desc())
        .limit(1)
        .with_for_update()
    )
    event = AuditEvent(
        event_id=str(uuid4()),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        actor_id=actor_id,
        correlation_id=correlation_id,
        payload=normalized_payload,
        previous_hash=latest.event_hash if latest else GENESIS_HASH,
        event_hash="",
        occurred_at=datetime.now(UTC),
    )
    event.event_hash = calculate_event_hash(event)
    session.add(event)
    session.flush()
    return event


@dataclass(frozen=True, slots=True)
class AuditVerification:
    valid: bool
    event_count: int
    head_hash: str
    broken_sequence: int | None = None


def verify_chain(session: Session) -> AuditVerification:
    events = list(
        session.scalars(select(AuditEvent).order_by(AuditEvent.sequence.asc()))
    )
    expected_previous = GENESIS_HASH
    for event in events:
        if (
            event.previous_hash != expected_previous
            or calculate_event_hash(event) != event.event_hash
        ):
            return AuditVerification(
                valid=False,
                event_count=len(events),
                head_hash=events[-1].event_hash if events else GENESIS_HASH,
                broken_sequence=event.sequence,
            )
        expected_previous = event.event_hash
    return AuditVerification(
        valid=True,
        event_count=len(events),
        head_hash=expected_previous,
    )
