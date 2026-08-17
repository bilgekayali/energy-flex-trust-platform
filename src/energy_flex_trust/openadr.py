"""OpenADR 3 contract boundary without bundled normative specification assets.

The OpenADR Alliance publishes the OpenAPI YAML as the normative OpenADR 3
reference. This module deliberately does not copy or approximate that schema.
Operators must supply a mapper and validator derived from the version of the
normative assets they have reviewed. The transport is separate so contract tests
can run without network access or credentials.
"""

from __future__ import annotations

from typing import Any, Protocol

from .ports import DispatchPublisher, DispatchSignal


class OpenAdr3EventMapper(Protocol):
    """Map a domain dispatch signal into a normative OpenADR 3 event document."""

    def map_dispatch(self, signal: DispatchSignal) -> dict[str, Any]: ...


class OpenAdr3SchemaValidator(Protocol):
    """Validate an event against operator-supplied normative schema artifacts."""

    def validate_event(self, document: dict[str, Any]) -> None: ...


class OpenAdr3Transport(Protocol):
    """Transmit a previously validated event using a downstream deduplication key."""

    def post_event(
        self,
        document: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> str: ...


class OpenAdr3ContractPublisher(DispatchPublisher):
    """Validate before transport and preserve the durable outbox idempotency key."""

    def __init__(
        self,
        mapper: OpenAdr3EventMapper,
        validator: OpenAdr3SchemaValidator,
        transport: OpenAdr3Transport,
    ) -> None:
        self.mapper = mapper
        self.validator = validator
        self.transport = transport

    def publish(
        self,
        signal: DispatchSignal,
        *,
        idempotency_key: str,
    ) -> str:
        if not idempotency_key.strip():
            raise ValueError("OpenADR transport idempotency key cannot be blank.")
        document = self.mapper.map_dispatch(signal)
        if not isinstance(document, dict) or not document:
            raise ValueError("OpenADR mapper returned an empty event document.")
        self.validator.validate_event(document)
        return self.transport.post_event(
            document,
            idempotency_key=idempotency_key,
        )


class RecordingOpenAdr3Transport:
    """Credential-free transport fixture for deterministic contract tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, Any], str]] = []

    def post_event(
        self,
        document: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> str:
        copied = dict(document)
        self.calls.append((copied, idempotency_key))
        return f"openadr-fixture:{idempotency_key}"
