"""Add reliable transactional outbox.

Revision ID: 0002_reliable_outbox
Revises: 0001_initial_schema
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_reliable_outbox"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=100), nullable=True),
        sa.Column("adapter_reference", sa.String(length=200), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "topic",
            "idempotency_key",
            name="uq_outbox_topic_idempotency_key",
        ),
    )
    for column in (
        "topic",
        "aggregate_id",
        "idempotency_key",
        "status",
        "available_at",
        "lease_expires_at",
    ):
        op.create_index(
            f"ix_outbox_messages_{column}",
            "outbox_messages",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in (
        "lease_expires_at",
        "available_at",
        "status",
        "idempotency_key",
        "aggregate_id",
        "topic",
    ):
        op.drop_index(
            f"ix_outbox_messages_{column}",
            table_name="outbox_messages",
        )
    op.drop_table("outbox_messages")
