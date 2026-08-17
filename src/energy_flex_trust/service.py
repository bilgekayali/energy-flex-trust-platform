"""Transactional application service and domain invariants."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TypeVar

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from .audit import append_event as append_audit_event
from .audit import canonical_json, sha256_json, verify_chain
from .domain import (
    Actor,
    ActorRole,
    AssetStatus,
    DispatchStatus,
    OfferStatus,
    ReservationStatus,
    require_role,
)
from .errors import (
    ConflictError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
)
from .models import (
    Asset,
    Dispatch,
    FlexOffer,
    IdempotencyRecord,
    MeterReading,
    Reservation,
    Settlement,
    new_id,
)
from .outbox import enqueue_dispatch
from .ports import DispatchSignal
from .schemas import (
    AssetCreate,
    DispatchCreate,
    MeterReadingCreate,
    OfferCreate,
    ReservationCreate,
)

Resource = TypeVar("Resource", Reservation, Dispatch, Settlement)
MONEY_QUANTUM = Decimal("0.000001")


class CoordinationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register_asset(self, command: AssetCreate, actor: Actor) -> Asset:
        require_role(actor, ActorRole.ASSET_OWNER)
        if command.owner_id != actor.actor_id:
            raise ForbiddenError("An asset owner can register only their own asset.")

        with self.session.begin():
            existing = self.session.scalar(
                select(Asset).where(Asset.external_id == command.external_id)
            )
            if existing:
                raise ConflictError(
                    f"Asset external_id '{command.external_id}' already exists."
                )
            asset = Asset(
                external_id=command.external_id,
                owner_id=command.owner_id,
                asset_type=command.asset_type.value,
                capacity_kw=command.capacity_kw,
                location_code=command.location_code,
                status=AssetStatus.ACTIVE.value,
            )
            self.session.add(asset)
            self.session.flush()
            append_audit_event(
                self.session,
                aggregate_type="asset",
                aggregate_id=asset.id,
                event_type="asset.registered",
                actor_id=actor.actor_id,
                correlation_id=new_id(),
                payload={
                    "external_id": asset.external_id,
                    "asset_type": asset.asset_type,
                    "capacity_kw": asset.capacity_kw,
                    "location_code": asset.location_code,
                },
            )
        return asset

    def create_offer(self, command: OfferCreate, actor: Actor) -> FlexOffer:
        require_role(actor, ActorRole.ASSET_OWNER)
        with self.session.begin():
            asset = self._asset(command.asset_id, for_update=True)
            if asset.owner_id != actor.actor_id:
                raise ForbiddenError("Only the asset owner can create its offer.")
            if asset.status != AssetStatus.ACTIVE.value:
                raise InvalidTransitionError(
                    "A suspended asset cannot create an offer."
                )
            if command.quantity_kw > asset.capacity_kw:
                raise ConflictError("Offer quantity exceeds the registered capacity.")

            offer = FlexOffer(
                asset_id=asset.id,
                window_start=command.window_start,
                window_end=command.window_end,
                direction=command.direction.value,
                quantity_kw=command.quantity_kw,
                price_per_kwh=command.price_per_kwh,
                status=OfferStatus.OPEN.value,
                created_by=actor.actor_id,
            )
            self.session.add(offer)
            self.session.flush()
            append_audit_event(
                self.session,
                aggregate_type="offer",
                aggregate_id=offer.id,
                event_type="offer.created",
                actor_id=actor.actor_id,
                correlation_id=new_id(),
                payload={
                    "asset_id": asset.id,
                    "direction": offer.direction,
                    "quantity_kw": offer.quantity_kw,
                    "price_per_kwh": offer.price_per_kwh,
                    "window_start": offer.window_start,
                    "window_end": offer.window_end,
                },
            )
        return offer

    def reserve_offer(
        self,
        offer_id: str,
        command: ReservationCreate,
        actor: Actor,
        idempotency_key: str,
    ) -> Reservation:
        require_role(actor, ActorRole.MARKET_OPERATOR)
        operation = "reserve_offer"
        request = {
            "offer_id": offer_id,
            "quantity_kw": command.quantity_kw,
            "actor_id": actor.actor_id,
        }
        request_hash = self._request_hash(request)
        with self.session.begin():
            existing = self._idempotent_resource(
                operation,
                idempotency_key,
                request_hash,
                Reservation,
            )
            if existing:
                return existing

            offer = self._offer(offer_id, for_update=True)
            if offer.status != OfferStatus.OPEN.value:
                raise InvalidTransitionError("Only an open offer can be reserved.")
            if command.quantity_kw > offer.quantity_kw:
                raise ConflictError("Reservation quantity exceeds the offer quantity.")

            reservation = Reservation(
                offer_id=offer.id,
                quantity_kw=command.quantity_kw,
                status=ReservationStatus.RESERVED.value,
                requested_by=actor.actor_id,
            )
            offer.status = OfferStatus.RESERVED.value
            self.session.add(reservation)
            self.session.flush()
            append_audit_event(
                self.session,
                aggregate_type="reservation",
                aggregate_id=reservation.id,
                event_type="offer.reserved",
                actor_id=actor.actor_id,
                correlation_id=idempotency_key,
                payload={
                    "offer_id": offer.id,
                    "quantity_kw": reservation.quantity_kw,
                },
            )
            self._store_idempotency(
                operation,
                idempotency_key,
                request_hash,
                "reservation",
                reservation.id,
            )
        return reservation

    def issue_dispatch(
        self,
        reservation_id: str,
        command: DispatchCreate,
        actor: Actor,
        idempotency_key: str,
    ) -> Dispatch:
        require_role(actor, ActorRole.MARKET_OPERATOR)
        operation = "issue_dispatch"
        request = {
            "reservation_id": reservation_id,
            **command.model_dump(mode="json"),
            "actor_id": actor.actor_id,
        }
        request_hash = self._request_hash(request)
        with self.session.begin():
            existing = self._idempotent_resource(
                operation,
                idempotency_key,
                request_hash,
                Dispatch,
            )
            if existing:
                return existing

            reservation = self._reservation(reservation_id, for_update=True)
            if reservation.status != ReservationStatus.RESERVED.value:
                raise InvalidTransitionError(
                    "Only a reserved reservation can be dispatched."
                )
            if command.target_kw > reservation.quantity_kw:
                raise ConflictError("Dispatch target exceeds reserved capacity.")

            offer = self._offer(reservation.offer_id)
            asset = self._asset(offer.asset_id)
            if self._utc(command.starts_at) < self._utc(
                offer.window_start
            ) or self._utc(command.ends_at) > self._utc(offer.window_end):
                raise ConflictError(
                    "Dispatch window must stay inside the offer window."
                )

            dispatch = Dispatch(
                reservation_id=reservation.id,
                target_kw=command.target_kw,
                starts_at=command.starts_at,
                ends_at=command.ends_at,
                status=DispatchStatus.QUEUED.value,
                issued_by=actor.actor_id,
            )
            self.session.add(dispatch)
            self.session.flush()
            outbox = enqueue_dispatch(
                self.session,
                DispatchSignal(
                    dispatch_id=dispatch.id,
                    asset_external_id=asset.external_id,
                    target_kw=dispatch.target_kw,
                    starts_at=dispatch.starts_at,
                    ends_at=dispatch.ends_at,
                ),
                idempotency_key=idempotency_key,
            )
            dispatch.adapter_reference = f"outbox:{outbox.id}"
            reservation.status = ReservationStatus.DISPATCH_PENDING.value
            append_audit_event(
                self.session,
                aggregate_type="dispatch",
                aggregate_id=dispatch.id,
                event_type="dispatch.queued",
                actor_id=actor.actor_id,
                correlation_id=idempotency_key,
                payload={
                    "reservation_id": reservation.id,
                    "target_kw": dispatch.target_kw,
                    "starts_at": dispatch.starts_at,
                    "ends_at": dispatch.ends_at,
                    "outbox_message_id": outbox.id,
                    "delivery_status": "queued",
                },
            )
            self._store_idempotency(
                operation,
                idempotency_key,
                request_hash,
                "dispatch",
                dispatch.id,
            )
        return dispatch

    def record_meter_reading(
        self,
        command: MeterReadingCreate,
        actor: Actor,
    ) -> MeterReading:
        require_role(actor, ActorRole.ASSET_OWNER, ActorRole.SYSTEM)
        fingerprint = self._request_hash(command.model_dump(mode="json"))
        with self.session.begin():
            asset = self._asset(command.asset_id)
            if actor.role == ActorRole.ASSET_OWNER and asset.owner_id != actor.actor_id:
                raise ForbiddenError(
                    "An asset owner can submit only their own reading."
                )
            existing = self.session.scalar(
                select(MeterReading).where(MeterReading.fingerprint == fingerprint)
            )
            if existing:
                return existing

            reading = MeterReading(
                asset_id=asset.id,
                interval_start=command.interval_start,
                interval_end=command.interval_end,
                energy_kwh=command.energy_kwh,
                source=command.source,
                fingerprint=fingerprint,
                recorded_by=actor.actor_id,
            )
            self.session.add(reading)
            self.session.flush()
            append_audit_event(
                self.session,
                aggregate_type="meter_reading",
                aggregate_id=reading.id,
                event_type="meter_reading.recorded",
                actor_id=actor.actor_id,
                correlation_id=fingerprint,
                payload={
                    "asset_id": asset.id,
                    "interval_start": reading.interval_start,
                    "interval_end": reading.interval_end,
                    "energy_kwh": reading.energy_kwh,
                    "source": reading.source,
                    "fingerprint": reading.fingerprint,
                },
            )
        return reading

    def settle_reservation(
        self,
        reservation_id: str,
        actor: Actor,
        idempotency_key: str,
    ) -> Settlement:
        require_role(actor, ActorRole.SETTLEMENT_ANALYST)
        operation = "settle_reservation"
        request_hash = self._request_hash(
            {"reservation_id": reservation_id, "actor_id": actor.actor_id}
        )
        with self.session.begin():
            existing = self._idempotent_resource(
                operation,
                idempotency_key,
                request_hash,
                Settlement,
            )
            if existing:
                return existing

            reservation = self._reservation(reservation_id, for_update=True)
            if reservation.status != ReservationStatus.DISPATCHED.value:
                raise InvalidTransitionError(
                    "Only a delivered dispatch can be settled."
                )
            dispatch = self.session.scalar(
                select(Dispatch).where(Dispatch.reservation_id == reservation.id)
            )
            if not dispatch:
                raise NotFoundError("No dispatch exists for the reservation.")
            if dispatch.status != DispatchStatus.ISSUED.value:
                raise InvalidTransitionError(
                    "Settlement requires a successfully published dispatch."
                )
            if actor.actor_id in {dispatch.issued_by, reservation.requested_by}:
                raise ForbiddenError(
                    "Settlement requires an actor separate from reservation "
                    "and dispatch."
                )

            offer = self._offer(reservation.offer_id)
            readings = list(
                self.session.scalars(
                    select(MeterReading)
                    .where(
                        and_(
                            MeterReading.asset_id == offer.asset_id,
                            MeterReading.interval_start >= dispatch.starts_at,
                            MeterReading.interval_end <= dispatch.ends_at,
                        )
                    )
                    .order_by(MeterReading.interval_start.asc(), MeterReading.id.asc())
                )
            )
            if not readings:
                raise ConflictError(
                    "Settlement requires at least one meter reading fully inside "
                    "the dispatch window."
                )

            delivered = sum(
                (reading.energy_kwh for reading in readings), Decimal("0")
            ).quantize(MONEY_QUANTUM)
            amount = (delivered * offer.price_per_kwh).quantize(
                MONEY_QUANTUM,
                rounding=ROUND_HALF_UP,
            )
            settlement = Settlement(
                id=new_id(),
                reservation_id=reservation.id,
                delivered_kwh=delivered,
                price_per_kwh=offer.price_per_kwh,
                amount=amount,
                evidence_manifest={},
                evidence_hash="",
                settled_by=actor.actor_id,
            )
            self.session.add(settlement)
            event = append_audit_event(
                self.session,
                aggregate_type="settlement",
                aggregate_id=settlement.id,
                event_type="settlement.calculated",
                actor_id=actor.actor_id,
                correlation_id=idempotency_key,
                payload={
                    "reservation_id": reservation.id,
                    "dispatch_id": dispatch.id,
                    "meter_reading_ids": [reading.id for reading in readings],
                    "delivered_kwh": delivered,
                    "price_per_kwh": offer.price_per_kwh,
                    "amount": amount,
                },
            )
            manifest = {
                "schema_version": "1.0",
                "settlement_id": settlement.id,
                "reservation_id": reservation.id,
                "offer_id": offer.id,
                "asset_id": offer.asset_id,
                "dispatch_id": dispatch.id,
                "meter_reading_ids": [reading.id for reading in readings],
                "delivered_kwh": format(delivered, "f"),
                "price_per_kwh": format(offer.price_per_kwh, "f"),
                "amount": format(amount, "f"),
                "audit_event_id": event.event_id,
                "audit_head_hash": event.event_hash,
            }
            settlement.evidence_manifest = manifest
            settlement.evidence_hash = sha256_json(manifest)
            reservation.status = ReservationStatus.COMPLETED.value
            dispatch.status = DispatchStatus.COMPLETED.value
            self._store_idempotency(
                operation,
                idempotency_key,
                request_hash,
                "settlement",
                settlement.id,
            )
        return settlement

    def settlement_evidence(
        self,
        settlement_id: str,
        actor: Actor,
    ) -> dict[str, object]:
        require_role(
            actor,
            ActorRole.AUDITOR,
            ActorRole.MARKET_OPERATOR,
            ActorRole.SETTLEMENT_ANALYST,
        )
        settlement = self.session.get(Settlement, settlement_id)
        if not settlement:
            raise NotFoundError(f"Settlement '{settlement_id}' was not found.")
        return {
            "manifest": settlement.evidence_manifest,
            "evidence_hash": settlement.evidence_hash,
            "hash_valid": sha256_json(settlement.evidence_manifest)
            == settlement.evidence_hash,
        }

    def audit_verification(self, actor: Actor):
        require_role(actor, ActorRole.AUDITOR)
        return verify_chain(self.session)

    def _asset(self, asset_id: str, *, for_update: bool = False) -> Asset:
        statement = select(Asset).where(Asset.id == asset_id)
        if for_update:
            statement = statement.with_for_update()
        asset = self.session.scalar(statement)
        if not asset:
            raise NotFoundError(f"Asset '{asset_id}' was not found.")
        return asset

    def _offer(self, offer_id: str, *, for_update: bool = False) -> FlexOffer:
        statement = select(FlexOffer).where(FlexOffer.id == offer_id)
        if for_update:
            statement = statement.with_for_update()
        offer = self.session.scalar(statement)
        if not offer:
            raise NotFoundError(f"Offer '{offer_id}' was not found.")
        return offer

    def _reservation(
        self,
        reservation_id: str,
        *,
        for_update: bool = False,
    ) -> Reservation:
        statement = select(Reservation).where(Reservation.id == reservation_id)
        if for_update:
            statement = statement.with_for_update()
        reservation = self.session.scalar(statement)
        if not reservation:
            raise NotFoundError(f"Reservation '{reservation_id}' was not found.")
        return reservation

    @staticmethod
    def _request_hash(payload: object) -> str:
        return sha256_json(payload)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _idempotent_resource(
        self,
        operation: str,
        key: str,
        request_hash: str,
        resource_model: type[Resource],
    ) -> Resource | None:
        if not key.strip():
            raise ConflictError("Idempotency-Key cannot be blank.")
        record = self.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.key == key,
            )
        )
        if not record:
            return None
        if record.request_hash != request_hash:
            raise ConflictError(
                "Idempotency-Key was already used with a different request."
            )
        resource = self.session.get(resource_model, record.resource_id)
        if not resource:
            raise ConflictError("Idempotency record points to a missing resource.")
        return resource

    def _store_idempotency(
        self,
        operation: str,
        key: str,
        request_hash: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        self.session.add(
            IdempotencyRecord(
                operation=operation,
                key=key,
                request_hash=request_hash,
                resource_type=resource_type,
                resource_id=resource_id,
                response_snapshot=canonical_json({"resource_id": resource_id}),
            )
        )
