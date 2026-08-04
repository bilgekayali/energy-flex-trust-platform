"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings with safe local defaults."""

    database_url: str = "sqlite:///./energy_flex_trust.db"
    environment: str = "development"

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "sqlite:///./energy_flex_trust.db",
            ),
            environment=os.getenv("APP_ENV", "development"),
        )
