"""Outbound integration ports and safe reliability test adapters."""

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
    def publish(
        self,
        signal: DispatchSignal,
        *,
        idempotency_key: str,
    ) -> str:
        """Publish a dispatch using a durable downstream deduplication key."""


class NoopDispatchPublisher:
    """Safe default: acknowledge without contacting a market or physical asset."""

    def publish(
        self,
        signal: DispatchSignal,
        *,
        idempotency_key: str,
    ) -> str:
        if not idempotency_key.strip():
            raise ValueError("Publisher idempotency key cannot be blank.")
        return f"noop:{signal.dispatch_id}"


class FaultInjectingDispatchPublisher:
    """Deterministically fail the first N publishes for recovery testing."""

    def __init__(
        self,
        delegate: DispatchPublisher,
        *,
        failures_before_success: int,
    ) -> None:
        if failures_before_success < 0:
            raise ValueError("failures_before_success cannot be negative.")
        self.delegate = delegate
        self.failures_before_success = failures_before_success
        self.attempts = 0

    def publish(
        self,
        signal: DispatchSignal,
        *,
        idempotency_key: str,
    ) -> str:
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise RuntimeError(
                f"Injected outbound failure #{self.attempts}."
            )
        return self.delegate.publish(
            signal,
            idempotency_key=idempotency_key,
        )
