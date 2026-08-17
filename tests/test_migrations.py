"""Versioned schema migration tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from energy_flex_trust.database import build_engine, initialize_database
from energy_flex_trust.models import Base


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_managed_schema_requires_migration(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'unmigrated.db'}"
    engine = build_engine(database_url)
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        initialize_database(engine, managed=True)


def test_initial_migration_matches_model_tables(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = _config(database_url)
    command.upgrade(config, "head")

    engine = build_engine(database_url)
    initialize_database(engine, managed=True)
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "alembic_version" in tables

    command.downgrade(config, "base")
    remaining = set(inspect(engine).get_table_names())
    assert not (set(Base.metadata.tables) & remaining)
