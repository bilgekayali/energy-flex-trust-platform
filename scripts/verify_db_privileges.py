"""Verify the v0.9 PostgreSQL runtime-role privilege matrix."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import create_engine, text


@dataclass(frozen=True, slots=True)
class RoleExpectation:
    role: str
    password: str
    grants: tuple[tuple[str, str], ...]
    denies: tuple[tuple[str, str], ...]


EXPECTATIONS = (
    RoleExpectation(
        role="flextrust_api",
        password="api-ci-only",
        grants=(("assets", "SELECT"), ("outbox_messages", "INSERT")),
        denies=(("assets", "DELETE"), ("public", "CREATE")),
    ),
    RoleExpectation(
        role="flextrust_worker",
        password="worker-ci-only",
        grants=(("outbox_messages", "UPDATE"), ("audit_events", "INSERT")),
        denies=(("assets", "INSERT"), ("settlements", "INSERT")),
    ),
    RoleExpectation(
        role="flextrust_recovery",
        password="recovery-ci-only",
        grants=(("outbox_messages", "UPDATE"), ("audit_events", "INSERT")),
        denies=(("assets", "UPDATE"), ("settlements", "INSERT")),
    ),
    RoleExpectation(
        role="flextrust_auditor",
        password="auditor-ci-only",
        grants=(("assets", "SELECT"), ("alembic_version", "SELECT")),
        denies=(("assets", "UPDATE"), ("audit_events", "INSERT")),
    ),
)


def _has_table_privilege(connection, table: str, privilege: str) -> bool:
    return bool(
        connection.scalar(
            text("SELECT has_table_privilege(current_user, :table, :privilege)"),
            {"table": table, "privilege": privilege},
        )
    )


def _has_schema_create(connection) -> bool:
    return bool(
        connection.scalar(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        )
    )


def verify(host: str, port: int, database: str) -> None:
    failures: list[str] = []
    for expectation in EXPECTATIONS:
        url = (
            f"postgresql+psycopg://{expectation.role}:{expectation.password}"
            f"@{host}:{port}/{database}"
        )
        engine = create_engine(url, future=True)
        try:
            with engine.connect() as connection:
                for resource, privilege in expectation.grants:
                    if not _has_table_privilege(connection, resource, privilege):
                        failures.append(
                            f"{expectation.role} missing {privilege} on {resource}"
                        )
                for resource, privilege in expectation.denies:
                    if resource == "public" and privilege == "CREATE":
                        observed = _has_schema_create(connection)
                    else:
                        observed = _has_table_privilege(
                            connection,
                            resource,
                            privilege,
                        )
                    if observed:
                        failures.append(
                            f"{expectation.role} unexpectedly has {privilege} "
                            f"on {resource}"
                        )
        finally:
            engine.dispose()

    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="flextrust")
    args = parser.parse_args()
    verify(args.host, args.port, args.database)
