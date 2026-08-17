"""Signed audit-chain checkpoints.

Checkpoints make a previously observed audit head independently verifiable. They do
not make the underlying database immutable and must be retained or anchored outside
the database if tail-truncation detection is required after compromise.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .audit import AuditVerification, canonical_json

CHECKPOINT_VERSION = "energy-flex-audit-checkpoint.v1"


class CheckpointSigner(Protocol):
    @property
    def key_id(self) -> str: ...

    def sign(self, payload: bytes) -> bytes: ...


@dataclass(frozen=True, slots=True)
class AuditCheckpoint:
    version: str
    key_id: str
    event_count: int
    head_hash: str
    issued_at: str
    signature: str

    def signing_payload(self) -> bytes:
        unsigned = asdict(self)
        unsigned.pop("signature")
        return canonical_json(unsigned).encode("utf-8")


@dataclass(frozen=True, slots=True)
class Ed25519SoftwareSigner:
    """In-process signer intended for tests and controlled reference deployments.

    Production key custody should normally be implemented behind ``CheckpointSigner``
    using an institution-owned KMS/HSM or signing service.
    """

    _key_id: str
    _private_key: Ed25519PrivateKey

    @property
    def key_id(self) -> str:
        return self._key_id

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)


def create_checkpoint(
    verification: AuditVerification,
    signer: CheckpointSigner,
    *,
    issued_at: datetime | None = None,
) -> AuditCheckpoint:
    if not verification.valid:
        raise ValueError("Cannot checkpoint an invalid audit chain.")
    timestamp = issued_at or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    unsigned = AuditCheckpoint(
        version=CHECKPOINT_VERSION,
        key_id=signer.key_id,
        event_count=verification.event_count,
        head_hash=verification.head_hash,
        issued_at=timestamp.astimezone(UTC).isoformat(),
        signature="",
    )
    signature = signer.sign(unsigned.signing_payload())
    return AuditCheckpoint(
        version=unsigned.version,
        key_id=unsigned.key_id,
        event_count=unsigned.event_count,
        head_hash=unsigned.head_hash,
        issued_at=unsigned.issued_at,
        signature=base64.b64encode(signature).decode("ascii"),
    )


def verify_checkpoint(
    checkpoint: AuditCheckpoint,
    *,
    trusted_public_keys: dict[str, str],
) -> bool:
    """Verify a checkpoint against base64-encoded raw Ed25519 public keys."""

    if checkpoint.version != CHECKPOINT_VERSION:
        return False
    encoded_key = trusted_public_keys.get(checkpoint.key_id)
    if encoded_key is None:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(encoded_key))
        signature = base64.b64decode(checkpoint.signature, validate=True)
        public_key.verify(signature, checkpoint.signing_payload())
    except (ValueError, InvalidSignature):
        return False
    return True
