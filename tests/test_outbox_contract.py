"""Outbox payload compatibility tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from energy_flex_trust.outbox import (
    DISPATCH_PAYLOAD_VERSION,
    dispatch_payload,
    dispatch_signal,
)
from energy_flex_trust.ports import DispatchSignal


def _signal() -> DispatchSignal:
    return DispatchSignal(
        dispatch_id="dispatch-contract-001",
        asset_external_id="asset-contract-001",
        target_kw=Decimal("40"),
        starts_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 8, 17, 13, 0, tzinfo=UTC),
    )


def test_new_payloads_are_explicitly_versioned() -> None:
    payload = dispatch_payload(_signal())
    assert payload["schema_version"] == DISPATCH_PAYLOAD_VERSION
    assert dispatch_signal(payload) == _signal()


def test_v03_legacy_payload_remains_readable_during_upgrade() -> None:
    payload = dispatch_payload(_signal())
    payload.pop("schema_version")
    assert dispatch_signal(payload) == _signal()


def test_unknown_payload_version_fails_closed() -> None:
    payload = dispatch_payload(_signal())
    payload["schema_version"] = "energy-flex-dispatch.v999"
    with pytest.raises(ValueError, match="version is unsupported"):
        dispatch_signal(payload)


def test_unknown_payload_shape_fails_closed() -> None:
    payload = dispatch_payload(_signal())
    payload["unexpected"] = "field"
    with pytest.raises(ValueError, match="unexpected shape"):
        dispatch_signal(payload)
