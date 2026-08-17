"""Outbox worker runtime-boundary tests."""

from __future__ import annotations

import pytest

from energy_flex_trust.config import Settings
from energy_flex_trust.worker import _resolve_publisher, run_once


def test_noop_worker_is_allowed_for_test_runtime() -> None:
    result = run_once(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        ),
        limit=1,
    )
    assert result.attempted == 0
    assert result.published == 0


def test_noop_worker_is_rejected_for_production_runtime() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@127.0.0.1/unused",
        environment="production",
        auth_mode="oidc",
        oidc_issuer="https://idp.example.invalid/",
        oidc_audience="energy-flex",
        oidc_jwks_json='{"keys": []}',
    )

    with pytest.raises(RuntimeError, match="institution-owned"):
        run_once(settings, limit=1)


def test_explicit_publisher_is_not_replaced() -> None:
    class Publisher:
        def publish(self, signal, *, idempotency_key: str) -> str:
            return f"explicit:{idempotency_key}"

    publisher = Publisher()
    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@127.0.0.1/unused",
        environment="production",
        auth_mode="oidc",
        oidc_issuer="https://idp.example.invalid/",
        oidc_audience="energy-flex",
        oidc_jwks_json='{"keys": []}',
    )

    assert _resolve_publisher(settings, publisher) is publisher
