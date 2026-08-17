"""Authenticated identity boundary tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.utils import base64url_encode

from energy_flex_trust.auth import (
    AuthenticationError,
    OidcVerifierConfig,
    verify_oidc_actor,
)
from energy_flex_trust.config import Settings
from energy_flex_trust.domain import ActorRole


def _integer(value: int) -> str:
    length = max(1, (value.bit_length() + 7) // 8)
    return base64url_encode(value.to_bytes(length, "big")).decode("ascii")


def _fixture() -> tuple[object, OidcVerifierConfig]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "institution-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": _integer(numbers.n),
                "e": _integer(numbers.e),
            }
        ]
    }
    config = OidcVerifierConfig(
        issuer="https://issuer.example.test",
        audience="energy-flex-api",
        jwks_json=json.dumps(jwks),
    )
    return private_key, config


def _token(private_key: object, **overrides: object) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": "https://issuer.example.test",
        "aud": "energy-flex-api",
        "sub": "operator-oidc-001",
        "energy_flex_role": "market_operator",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "institution-key-1"},
    )


def test_oidc_verifier_resolves_exact_actor_and_role() -> None:
    private_key, config = _fixture()
    actor = verify_oidc_actor(_token(private_key), config)
    assert actor.actor_id == "operator-oidc-001"
    assert actor.role is ActorRole.MARKET_OPERATOR


def test_oidc_verifier_rejects_ambiguous_role_claim() -> None:
    private_key, config = _fixture()
    token = _token(
        private_key,
        energy_flex_role=["market_operator", "auditor"],
    )
    with pytest.raises(AuthenticationError):
        verify_oidc_actor(token, config)


def test_oidc_verifier_rejects_wrong_audience() -> None:
    private_key, config = _fixture()
    token = _token(private_key, aud="other-service")
    with pytest.raises(AuthenticationError):
        verify_oidc_actor(token, config)


def test_non_development_runtime_rejects_header_auth() -> None:
    settings = Settings(environment="production", auth_mode="development_headers")
    with pytest.raises(ValueError, match="AUTH_MODE=oidc"):
        settings.validate_runtime()


def test_oidc_runtime_requires_pinned_trust_configuration() -> None:
    settings = Settings(environment="production", auth_mode="oidc")
    with pytest.raises(ValueError, match="OIDC_ISSUER"):
        settings.validate_runtime()
