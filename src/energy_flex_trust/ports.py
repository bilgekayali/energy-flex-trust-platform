"""Outbound integration ports.

The v0.1 reference implementation deliberately ships without a live grid-control
adapter. An OpenADR 3 adapter can implement this boundary without changing the
domain transaction flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DispatchSignal:
    dispatch_id: str
    asset_external_id: str
    target_kw: Decimal
    starts_at: datetime
    ends_at: datetime


class DispatchPublisher(Protocol):
    def publish(self, signal: DispatchSignal) -> str:
        """Publish a synthetic or external dispatch and return a reference."""


class NoopDispatchPublisher:
    """Safe default: records intent without contacting a real energy asset."""

    def publish(self, signal: DispatchSignal) -> str:
        return f"noop:{signal.dispatch_id}"
