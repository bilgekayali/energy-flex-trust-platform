"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings with safe local defaults."""

    database_url: str = "sqlite:///./energy_flex_trust.db"
    environment: str = "development"
    auth_mode: str = "development_headers"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_json: str = ""
    oidc_role_claim: str = "energy_flex_role"
    oidc_subject_claim: str = "sub"

    def validate_runtime(self) -> None:
        if self.auth_mode not in {"development_headers", "oidc"}:
            raise ValueError("AUTH_MODE must be 'development_headers' or 'oidc'.")
        if self.environment not in {"development", "test"} and self.auth_mode != "oidc":
            raise ValueError(
                "Non-development environments require AUTH_MODE=oidc; "
                "caller-asserted actor headers are not an authentication boundary."
            )
        if self.auth_mode == "oidc" and (
            not self.oidc_issuer or not self.oidc_audience or not self.oidc_jwks_json
        ):
            raise ValueError(
                "OIDC mode requires OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_JSON."
            )

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "sqlite:///./energy_flex_trust.db",
            ),
            environment=os.getenv("APP_ENV", "development"),
            auth_mode=os.getenv("AUTH_MODE", "development_headers"),
            oidc_issuer=os.getenv("OIDC_ISSUER", ""),
            oidc_audience=os.getenv("OIDC_AUDIENCE", ""),
            oidc_jwks_json=os.getenv("OIDC_JWKS_JSON", ""),
            oidc_role_claim=os.getenv("OIDC_ROLE_CLAIM", "energy_flex_role"),
            oidc_subject_claim=os.getenv("OIDC_SUBJECT_CLAIM", "sub"),
        )
