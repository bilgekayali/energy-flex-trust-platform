"""OpenADR 3 adapter-boundary contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from energy_flex_trust.openadr import (
    OpenAdr3ContractPublisher,
    RecordingOpenAdr3Transport,
)
from energy_flex_trust.ports import DispatchSignal


class FixtureMapper:
    """Synthetic mapper used only to exercise the adapter contract."""

    def map_dispatch(self, signal: DispatchSignal) -> dict[str, Any]:
        return {
            "fixture": "openadr3-event-contract",
            "dispatch_id": signal.dispatch_id,
            "asset_external_id": signal.asset_external_id,
            "target_kw": format(signal.target_kw, "f"),
            "starts_at": signal.starts_at.isoformat(),
            "ends_at": signal.ends_at.isoformat(),
        }


class RecordingValidator:
    def __init__(self, *, reject: bool = False) -> None:
        self.reject = reject
        self.documents: list[dict[str, Any]] = []

    def validate_event(self, document: dict[str, Any]) -> None:
        self.documents.append(dict(document))
        if self.reject:
            raise ValueError("synthetic schema rejection")


def _signal() -> DispatchSignal:
    start = datetime(2026, 8, 18, 18, 0, tzinfo=UTC)
    return DispatchSignal(
        dispatch_id="dispatch-openadr-001",
        asset_external_id="BATTERY-GB-OPENADR-001",
        target_kw=Decimal("25.5"),
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
    )


def test_validated_event_preserves_outbox_idempotency_key() -> None:
    validator = RecordingValidator()
    transport = RecordingOpenAdr3Transport()
    publisher = OpenAdr3ContractPublisher(
        FixtureMapper(),
        validator,
        transport,
    )

    reference = publisher.publish(
        _signal(),
        idempotency_key="outbox-openadr-001",
    )

    assert reference == "openadr-fixture:outbox-openadr-001"
    assert len(validator.documents) == 1
    assert transport.calls == [
        (validator.documents[0], "outbox-openadr-001")
    ]


def test_schema_rejection_blocks_transport() -> None:
    validator = RecordingValidator(reject=True)
    transport = RecordingOpenAdr3Transport()
    publisher = OpenAdr3ContractPublisher(
        FixtureMapper(),
        validator,
        transport,
    )

    with pytest.raises(ValueError, match="schema rejection"):
        publisher.publish(_signal(), idempotency_key="outbox-openadr-002")

    assert len(validator.documents) == 1
    assert transport.calls == []


def test_blank_idempotency_key_is_rejected_before_mapping() -> None:
    validator = RecordingValidator()
    transport = RecordingOpenAdr3Transport()
    publisher = OpenAdr3ContractPublisher(
        FixtureMapper(),
        validator,
        transport,
    )

    with pytest.raises(ValueError, match="idempotency"):
        publisher.publish(_signal(), idempotency_key=" ")

    assert validator.documents == []
    assert transport.calls == []
