"""Transactional outbox delivery with bounded retry and crash recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Callable
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from .audit import append_event as append_audit_event
from .domain import DispatchStatus, ReservationStatus
from .models import Dispatch, OutboxMessage, Reservation, utc_now
from .ports import DispatchPublisher, DispatchSignal

DISPATCH_TOPIC = "dispatch.publish"
Clock = Callable[[], datetime]


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class ClaimedMessage:
    id: str
    aggregate_id: str
    idempotency_key: str
    payload: dict[str, object]
    attempts: int
    claim_token: str


@dataclass(frozen=True, slots=True)
class OutboxRunResult:
    attempted: int = 0
    published: int = 0
    retried: int = 0
    dead: int = 0


@dataclass(frozen=True, slots=True)
class OutboxSnapshot:
    pending: int
    processing: int
    published: int
    dead: int
    due: int
    oldest_pending_age_seconds: float | None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def dispatch_payload(signal: DispatchSignal) -> dict[str, object]:
    """Serialize a dispatch signal into deterministic JSON-compatible data."""

    return {
        "dispatch_id": signal.dispatch_id,
        "asset_external_id": signal.asset_external_id,
        "target_kw": format(signal.target_kw, "f"),
        "starts_at": _as_utc(signal.starts_at).isoformat(),
        "ends_at": _as_utc(signal.ends_at).isoformat(),
    }


def dispatch_signal(payload: dict[str, object]) -> DispatchSignal:
    """Restore a validated dispatch signal from an outbox payload."""

    required = {
        "dispatch_id",
        "asset_external_id",
        "target_kw",
        "starts_at",
        "ends_at",
    }
    if set(payload) != required:
        raise ValueError("Dispatch outbox payload has an unexpected shape.")
    return DispatchSignal(
        dispatch_id=str(payload["dispatch_id"]),
        asset_external_id=str(payload["asset_external_id"]),
        target_kw=Decimal(str(payload["target_kw"])),
        starts_at=datetime.fromisoformat(str(payload["starts_at"])),
        ends_at=datetime.fromisoformat(str(payload["ends_at"])),
    )


def enqueue_dispatch(
    session: Session,
    signal: DispatchSignal,
    *,
    idempotency_key: str,
) -> OutboxMessage:
    """Persist outbound dispatch work inside the caller's domain transaction."""

    if not idempotency_key.strip():
        raise ValueError("Outbox idempotency key cannot be blank.")
    message = OutboxMessage(
        topic=DISPATCH_TOPIC,
        aggregate_id=signal.dispatch_id,
        idempotency_key=idempotency_key,
        payload=dispatch_payload(signal),
        status=OutboxStatus.PENDING.value,
    )
    session.add(message)
    session.flush()
    return message


class OutboxWorker:
    """Lease, publish, and finalize durable outbound work.

    Publication is intentionally outside the database transaction. A crash after a
    successful external publish but before finalization can cause a replay, so the
    publisher receives the durable idempotency key and must deduplicate downstream.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        publisher: DispatchPublisher,
        *,
        worker_id: str = "outbox-worker",
        max_attempts: int = 5,
        base_retry_seconds: int = 1,
        max_retry_seconds: int = 60,
        lease_seconds: int = 30,
        clock: Clock = utc_now,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least one.")
        if base_retry_seconds < 1 or max_retry_seconds < base_retry_seconds:
            raise ValueError("Retry bounds are invalid.")
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be at least one.")
        self.session_factory = session_factory
        self.publisher = publisher
        self.worker_id = worker_id
        self.max_attempts = max_attempts
        self.base_retry_seconds = base_retry_seconds
        self.max_retry_seconds = max_retry_seconds
        self.lease_seconds = lease_seconds
        self.clock = clock

    def run_once(self, *, limit: int = 10) -> OutboxRunResult:
        if limit < 1:
            raise ValueError("limit must be at least one.")
        attempted = published = retried = dead = 0
        for _ in range(limit):
            claimed = self._claim_one()
            if claimed is None:
                break
            attempted += 1
            try:
                reference = self.publisher.publish(
                    dispatch_signal(claimed.payload),
                    idempotency_key=claimed.idempotency_key,
                )
            except Exception as exc:  # noqa: BLE001 - adapter boundary.
                terminal = self._record_failure(claimed, exc)
                if terminal:
                    dead += 1
                else:
                    retried += 1
            else:
                if self._record_success(claimed, reference):
                    published += 1
        return OutboxRunResult(
            attempted=attempted,
            published=published,
            retried=retried,
            dead=dead,
        )

    def _claim_one(self) -> ClaimedMessage | None:
        now = _as_utc(self.clock())
        with self.session_factory() as session:
            with session.begin():
                statement = (
                    select(OutboxMessage)
                    .where(
                        OutboxMessage.topic == DISPATCH_TOPIC,
                        OutboxMessage.available_at <= now,
                        or_(
                            OutboxMessage.status == OutboxStatus.PENDING.value,
                            and_(
                                OutboxMessage.status
                                == OutboxStatus.PROCESSING.value,
                                OutboxMessage.lease_expires_at.is_not(None),
                                OutboxMessage.lease_expires_at <= now,
                            ),
                        ),
                    )
                    .order_by(
                        OutboxMessage.available_at.asc(),
                        OutboxMessage.created_at.asc(),
                        OutboxMessage.id.asc(),
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                message = session.scalar(statement)
                if message is None:
                    return None
                claim_token = f"{self.worker_id}:{uuid4()}"
                message.status = OutboxStatus.PROCESSING.value
                message.attempts += 1
                message.locked_by = claim_token
                message.lease_expires_at = now + timedelta(
                    seconds=self.lease_seconds
                )
                message.updated_at = now
                return ClaimedMessage(
                    id=message.id,
                    aggregate_id=message.aggregate_id,
                    idempotency_key=message.idempotency_key,
                    payload=dict(message.payload),
                    attempts=message.attempts,
                    claim_token=claim_token,
                )

    def _record_success(self, claimed: ClaimedMessage, reference: str) -> bool:
        now = _as_utc(self.clock())
        with self.session_factory() as session:
            with session.begin():
                message = session.get(OutboxMessage, claimed.id)
                if message is None or message.locked_by != claimed.claim_token:
                    return False
                dispatch = session.get(Dispatch, claimed.aggregate_id)
                if dispatch is None:
                    raise RuntimeError("Outbox dispatch aggregate no longer exists.")
                reservation = session.get(Reservation, dispatch.reservation_id)
                if reservation is None:
                    raise RuntimeError("Dispatch reservation no longer exists.")
                message.status = OutboxStatus.PUBLISHED.value
                message.adapter_reference = reference
                message.published_at = now
                message.lease_expires_at = None
                message.locked_by = None
                message.last_error = None
                message.updated_at = now
                dispatch.adapter_reference = reference
                dispatch.status = DispatchStatus.ISSUED.value
                reservation.status = ReservationStatus.DISPATCHED.value
                append_audit_event(
                    session,
                    aggregate_type="dispatch",
                    aggregate_id=dispatch.id,
                    event_type="dispatch.published",
                    actor_id=f"system:{self.worker_id}",
                    correlation_id=claimed.idempotency_key,
                    payload={
                        "outbox_message_id": message.id,
                        "adapter_reference": reference,
                        "attempt": message.attempts,
                    },
                )
                return True

    def _record_failure(self, claimed: ClaimedMessage, exc: Exception) -> bool:
        now = _as_utc(self.clock())
        with self.session_factory() as session:
            with session.begin():
                message = session.get(OutboxMessage, claimed.id)
                if message is None or message.locked_by != claimed.claim_token:
                    return False
                error_text = f"{type(exc).__name__}: {exc}"[:2000]
                message.last_error = error_text
                message.lease_expires_at = None
                message.locked_by = None
                message.updated_at = now
                if message.attempts >= self.max_attempts:
                    message.status = OutboxStatus.DEAD.value
                    dispatch = session.get(Dispatch, claimed.aggregate_id)
                    if dispatch is not None:
                        dispatch.status = DispatchStatus.REJECTED.value
                        reservation = session.get(
                            Reservation,
                            dispatch.reservation_id,
                        )
                        if reservation is not None:
                            reservation.status = ReservationStatus.CANCELLED.value
                        append_audit_event(
                            session,
                            aggregate_type="dispatch",
                            aggregate_id=dispatch.id,
                            event_type="dispatch.delivery_failed",
                            actor_id=f"system:{self.worker_id}",
                            correlation_id=claimed.idempotency_key,
                            payload={
                                "outbox_message_id": message.id,
                                "attempts": message.attempts,
                                "error": error_text,
                            },
                        )
                    return True
                message.status = OutboxStatus.PENDING.value
                message.available_at = now + timedelta(
                    seconds=self._retry_delay(message.attempts)
                )
                return False

    def _retry_delay(self, attempts: int) -> int:
        delay = self.base_retry_seconds * (2 ** max(0, attempts - 1))
        return min(delay, self.max_retry_seconds)


def outbox_snapshot(
    session: Session,
    *,
    now: datetime | None = None,
) -> OutboxSnapshot:
    """Return low-cardinality operational health metrics for the outbox."""

    observed_at = _as_utc(now or utc_now())
    grouped = dict(
        session.execute(
            select(OutboxMessage.status, func.count(OutboxMessage.id)).group_by(
                OutboxMessage.status
            )
        ).all()
    )
    due = session.scalar(
        select(func.count(OutboxMessage.id)).where(
            OutboxMessage.status == OutboxStatus.PENDING.value,
            OutboxMessage.available_at <= observed_at,
        )
    ) or 0
    oldest = session.scalar(
        select(func.min(OutboxMessage.created_at)).where(
            OutboxMessage.status == OutboxStatus.PENDING.value
        )
    )
    age = None
    if oldest is not None:
        age = max(0.0, (observed_at - _as_utc(oldest)).total_seconds())
    return OutboxSnapshot(
        pending=int(grouped.get(OutboxStatus.PENDING.value, 0)),
        processing=int(grouped.get(OutboxStatus.PROCESSING.value, 0)),
        published=int(grouped.get(OutboxStatus.PUBLISHED.value, 0)),
        dead=int(grouped.get(OutboxStatus.DEAD.value, 0)),
        due=int(due),
        oldest_pending_age_seconds=age,
    )
