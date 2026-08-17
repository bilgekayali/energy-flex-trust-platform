"""SQLAlchemy engine, schema and session construction."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base

EXPECTED_SCHEMA_REVISION = "0002_reliable_outbox"


def build_engine(database_url: str) -> Engine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url.endswith(":memory:"):
            kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, **kwargs)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(
            dbapi_connection: sqlite3.Connection,
            _connection_record: object,
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def _verify_managed_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables)
    missing = expected_tables - table_names
    if "alembic_version" not in table_names:
        raise RuntimeError(
            "Managed database has no Alembic revision. Run 'alembic upgrade head'."
        )
    if missing:
        names = ", ".join(sorted(missing))
        raise RuntimeError(f"Managed database is missing required tables: {names}.")
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != EXPECTED_SCHEMA_REVISION:
        raise RuntimeError(
            "Managed database revision is incompatible: "
            f"expected {EXPECTED_SCHEMA_REVISION}, found {revision!r}."
        )


def initialize_database(engine: Engine, *, managed: bool = False) -> None:
    """Initialize a local schema or verify an operator-managed migrated schema.

    Local development and tests may use SQLAlchemy ``create_all`` for convenience.
    Non-development deployments must apply the versioned Alembic migration before
    application startup and are verified fail-closed here.
    """

    if managed:
        _verify_managed_schema(engine)
        return
    Base.metadata.create_all(engine)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
