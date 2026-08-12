"""Add email_campaigns and webhook_logs tables.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── email_campaigns ───────────────────────────────────────────────────────
    op.create_table(
        "email_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("target_segment", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("estimated_recipients", sa.Integer(), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_email_campaigns_status", "email_campaigns", ["status"])
    op.create_index("ix_email_campaigns_created_at", "email_campaigns", ["created_at"])

    # ── webhook_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "webhook_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="received"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_logs_source", "webhook_logs", ["source"])
    op.create_index("ix_webhook_logs_status", "webhook_logs", ["status"])
    op.create_index("ix_webhook_logs_event_type", "webhook_logs", ["event_type"])
    op.create_index("ix_webhook_logs_created_at", "webhook_logs", ["created_at"])
    op.create_index("ix_webhook_logs_bot_id", "webhook_logs", ["bot_id"])


def downgrade() -> None:
    op.drop_index("ix_webhook_logs_bot_id", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_created_at", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_event_type", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_status", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_source", table_name="webhook_logs")
    op.drop_table("webhook_logs")

    op.drop_index("ix_email_campaigns_created_at", table_name="email_campaigns")
    op.drop_index("ix_email_campaigns_status", table_name="email_campaigns")
    op.drop_table("email_campaigns")
