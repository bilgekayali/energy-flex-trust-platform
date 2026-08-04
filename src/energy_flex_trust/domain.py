"""Domain types and authorization policy primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import ForbiddenError


class AssetType(StrEnum):
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    HEAT_PUMP = "heat_pump"
    INDUSTRIAL_LOAD = "industrial_load"


class AssetStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class FlexDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class OfferStatus(StrEnum):
    OPEN = "open"
    RESERVED = "reserved"
    CANCELLED = "cancelled"


class ReservationStatus(StrEnum):
    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DispatchStatus(StrEnum):
    ISSUED = "issued"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ActorRole(StrEnum):
    ASSET_OWNER = "asset_owner"
    MARKET_OPERATOR = "market_operator"
    SETTLEMENT_ANALYST = "settlement_analyst"
    AUDITOR = "auditor"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class Actor:
    actor_id: str
    role: ActorRole


def require_role(actor: Actor, *allowed: ActorRole) -> None:
    """Reject an actor whose asserted role is outside the policy boundary."""

    if actor.role not in allowed:
        expected = ", ".join(role.value for role in allowed)
        raise ForbiddenError(
            f"Role '{actor.role.value}' cannot perform this operation; "
            f"expected one of: {expected}."
        )
