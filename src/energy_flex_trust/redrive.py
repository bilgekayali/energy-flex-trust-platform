"""Controlled authorization of terminal outbox re-drive operations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import append_event as append_audit_event
from .domain import Actor, ActorRole, DispatchStatus, ReservationStatus, require_role
from .errors import ConflictError, InvalidTransitionError, NotFoundError
from .models import Dispatch, OutboxMessage, Reservation, utc_now
from .outbox import DISPATCH_TOPIC, OutboxStatus


@dataclass(frozen=True, slots=True)
class RedriveAuthorization:
    message_id: str
    dispatch_id: str
    idempotency_key: str
    previous_attempts: int
    status: str


def authorize_dead_dispatch_redrive(
    session: Session,
    *,
    actor: Actor,
    message_id: str,
    dispatch_id: str,
    reason: str,
) -> RedriveAuthorization:
    """Re-arm one terminal dispatch while preserving its deduplication identity.

    This operation does not publish anything. It only restores a previously dead
    outbox message and its aggregate state to the normal pending path. A subsequent
    worker attempt still uses the original durable idempotency key, which is
    critical when an earlier external publish may have succeeded before local
    acknowledgement was lost.
    """

    require_role(actor, ActorRole.RECOVERY_OPERATOR)
    normalized_reason = " ".join(reason.split())
    if len(normalized_reason) < 12:
        raise ValueError(
            "A specific re-drive reason of at least 12 characters is required."
        )

    with session.begin():
        message = session.scalar(
            select(OutboxMessage)
            .where(OutboxMessage.id == message_id)
            .with_for_update()
        )
        if message is None:
            raise NotFoundError(f"Outbox message '{message_id}' was not found.")
        if message.topic != DISPATCH_TOPIC:
            raise ConflictError("Only dispatch outbox messages can be re-driven here.")
        if message.aggregate_id != dispatch_id:
            raise ConflictError(
                "Outbox message and dispatch identifiers do not match."
            )
        if message.status != OutboxStatus.DEAD.value:
            raise InvalidTransitionError("Only a terminal dead message can be re-driven.")

        dispatch = session.scalar(
            select(Dispatch).where(Dispatch.id == dispatch_id).with_for_update()
        )
        if dispatch is None:
            raise NotFoundError(f"Dispatch '{dispatch_id}' was not found.")
        reservation = session.scalar(
            select(Reservation)
            .where(Reservation.id == dispatch.reservation_id)
            .with_for_update()
        )
        if reservation is None:
            raise NotFoundError(
                f"Reservation '{dispatch.reservation_id}' was not found."
            )
        if dispatch.status != DispatchStatus.REJECTED.value:
            raise InvalidTransitionError(
                "Re-drive requires the dispatch to be in rejected state."
            )
        if reservation.status != ReservationStatus.CANCELLED.value:
            raise InvalidTransitionError(
                "Re-drive requires the reservation to be in cancelled state."
            )

        previous_attempts = message.attempts
        previous_error = message.last_error or ""
        error_digest = hashlib.sha256(previous_error.encode("utf-8")).hexdigest()
        now = utc_now()

        message.status = OutboxStatus.PENDING.value
        message.attempts = 0
        message.available_at = now
        message.lease_expires_at = None
        message.locked_by = None
        message.adapter_reference = None
        message.last_error = None
        message.published_at = None
        message.updated_at = now

        dispatch.status = DispatchStatus.QUEUED.value
        dispatch.adapter_reference = f"outbox:{message.id}"
        reservation.status = ReservationStatus.DISPATCH_PENDING.value

        append_audit_event(
            session,
            aggregate_type="dispatch",
            aggregate_id=dispatch.id,
            event_type="dispatch.redrive_authorized",
            actor_id=actor.actor_id,
            correlation_id=message.idempotency_key,
            payload={
                "outbox_message_id": message.id,
                "reason": normalized_reason,
                "previous_attempts": previous_attempts,
                "previous_error_sha256": error_digest,
                "idempotency_key_reused": True,
            },
        )

        return RedriveAuthorization(
            message_id=message.id,
            dispatch_id=dispatch.id,
            idempotency_key=message.idempotency_key,
            previous_attempts=previous_attempts,
            status=message.status,
        )
