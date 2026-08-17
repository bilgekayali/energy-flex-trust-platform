"""Deterministic authenticated-identity boundary for OIDC access tokens.

The verifier consumes a caller-configured JWKS document. It never retrieves keys
from the network, follows discovery URLs, or accepts caller-selected algorithms.
Operational key distribution and rotation remain an institution-owned concern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import InvalidTokenError, PyJWK

from .domain import Actor, ActorRole
from .errors import DomainError

ALLOWED_ALGORITHMS = frozenset({"RS256", "ES256"})


class AuthenticationError(DomainError):
    code = "authentication_failed"
    status_code = 401


@dataclass(frozen=True, slots=True)
class OidcVerifierConfig:
    issuer: str
    audience: str
    jwks_json: str
    role_claim: str = "energy_flex_role"
    subject_claim: str = "sub"

    def validate(self) -> None:
        if not self.issuer or not self.audience or not self.jwks_json:
            raise ValueError("OIDC issuer, audience and JWKS are required.")
        if not self.role_claim or not self.subject_claim:
            raise ValueError("OIDC subject and role claim names are required.")


def _load_keys(jwks_json: str) -> dict[str, dict[str, Any]]:
    try:
        document = json.loads(jwks_json)
    except json.JSONDecodeError as exc:
        raise AuthenticationError("Configured OIDC JWKS is not valid JSON.") from exc
    keys = document.get("keys")
    if not isinstance(keys, list) or not keys:
        raise AuthenticationError("Configured OIDC JWKS contains no keys.")

    indexed: dict[str, dict[str, Any]] = {}
    for key in keys:
        if not isinstance(key, dict):
            raise AuthenticationError("Configured OIDC JWKS contains an invalid key.")
        kid = key.get("kid")
        if not isinstance(kid, str) or not kid:
            raise AuthenticationError("Every configured OIDC JWK requires a kid.")
        if kid in indexed:
            raise AuthenticationError("Configured OIDC JWKS contains duplicate kids.")
        indexed[kid] = key
    return indexed


def _resolve_role(value: object) -> ActorRole:
    if isinstance(value, str):
        role_value = value
    elif isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        role_value = value[0]
    else:
        raise AuthenticationError(
            "OIDC role claim must contain exactly one Energy Flex role."
        )
    try:
        return ActorRole(role_value)
    except ValueError as exc:
        raise AuthenticationError("OIDC token contains an unsupported role.") from exc


def verify_oidc_actor(token: str, config: OidcVerifierConfig) -> Actor:
    """Verify an OIDC JWT against a pinned local trust configuration."""

    config.validate()
    try:
        header = jwt.get_unverified_header(token)
    except InvalidTokenError as exc:
        raise AuthenticationError("Bearer token header is invalid.") from exc

    algorithm = header.get("alg")
    kid = header.get("kid")
    if algorithm not in ALLOWED_ALGORITHMS:
        raise AuthenticationError("Bearer token algorithm is not allowed.")
    if not isinstance(kid, str) or not kid:
        raise AuthenticationError("Bearer token requires a key identifier.")

    key_data = _load_keys(config.jwks_json).get(kid)
    if key_data is None:
        raise AuthenticationError("Bearer token key is not trusted.")
    if key_data.get("alg") not in (None, algorithm):
        raise AuthenticationError("Bearer token algorithm does not match its JWK.")

    try:
        key = PyJWK.from_dict(key_data, algorithm=algorithm).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[algorithm],
            audience=config.audience,
            issuer=config.issuer,
            options={
                "require": [
                    "exp",
                    "iat",
                    config.subject_claim,
                    config.role_claim,
                ]
            },
        )
    except (InvalidTokenError, ValueError) as exc:
        raise AuthenticationError("Bearer token verification failed.") from exc

    subject = claims.get(config.subject_claim)
    if not isinstance(subject, str) or not subject.strip():
        raise AuthenticationError("Bearer token subject is invalid.")
    return Actor(actor_id=subject, role=_resolve_role(claims.get(config.role_claim)))
