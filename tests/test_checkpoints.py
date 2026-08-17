"""Signed audit checkpoint tests."""

from __future__ import annotations

import base64
from dataclasses import replace
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from energy_flex_trust.audit import AuditVerification
from energy_flex_trust.checkpoints import (
    AuditCheckpoint,
    Ed25519SoftwareSigner,
    create_checkpoint,
    verify_checkpoint,
)


def _keys() -> tuple[Ed25519SoftwareSigner, dict[str, str]]:
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signer = Ed25519SoftwareSigner("checkpoint-key-1", private_key)
    trust = {
        "checkpoint-key-1": base64.b64encode(public_bytes).decode("ascii")
    }
    return signer, trust


def test_checkpoint_verifies_exact_chain_head() -> None:
    signer, trust = _keys()
    checkpoint = create_checkpoint(
        AuditVerification(valid=True, event_count=7, head_hash="a" * 64),
        signer,
        issued_at=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
    )
    assert checkpoint.event_count == 7
    assert checkpoint.head_hash == "a" * 64
    assert verify_checkpoint(checkpoint, trusted_public_keys=trust)


def test_checkpoint_rejects_tampered_head() -> None:
    signer, trust = _keys()
    checkpoint = create_checkpoint(
        AuditVerification(valid=True, event_count=7, head_hash="a" * 64),
        signer,
    )
    tampered = replace(checkpoint, head_hash="b" * 64)
    assert not verify_checkpoint(tampered, trusted_public_keys=trust)


def test_checkpoint_rejects_untrusted_key() -> None:
    signer, _trust = _keys()
    checkpoint = create_checkpoint(
        AuditVerification(valid=True, event_count=1, head_hash="c" * 64),
        signer,
    )
    assert not verify_checkpoint(checkpoint, trusted_public_keys={})


def test_checkpoint_rejects_invalid_chain() -> None:
    signer, _trust = _keys()
    verification = AuditVerification(
        valid=False,
        event_count=1,
        head_hash="d" * 64,
        broken_sequence=1,
    )
    try:
        create_checkpoint(verification, signer)
    except ValueError as exc:
        assert "invalid audit chain" in str(exc)
    else:
        raise AssertionError("invalid audit chain was checkpointed")


def test_checkpoint_version_is_signed() -> None:
    signer, trust = _keys()
    checkpoint = create_checkpoint(
        AuditVerification(valid=True, event_count=2, head_hash="e" * 64),
        signer,
    )
    changed = AuditCheckpoint(
        version="unknown.v9",
        key_id=checkpoint.key_id,
        event_count=checkpoint.event_count,
        head_hash=checkpoint.head_hash,
        issued_at=checkpoint.issued_at,
        signature=checkpoint.signature,
    )
    assert not verify_checkpoint(changed, trusted_public_keys=trust)
