"""users: telegram_chat_id + telegram_linked_at; notifications table for dashboard bell

Revision ID: h8c9d1e2f3g4
Revises: g7b8c9d1e2f3
Create Date: 2026-06-01

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8c9d1e2f3g4"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: Telegram linking columns ---
    op.add_column(
        "users",
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("telegram_link_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("telegram_linked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- owner_notifications: dashboard bell ---
    op.create_table(
        "owner_notifications",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("body", sa.String(length=2048), nullable=True),
        sa.Column(
            "reference_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Lead id, bot id, or other entity this notification refers to.",
        ),
        sa.Column("reference_type", sa.String(length=32), nullable=True),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "kind IN ('new_lead', 'lead_update', 'bot_status', 'system')",
            name="ck_owner_notifications_kind_allowed",
        ),
    )
    op.create_index(
        "ix_owner_notifications_owner_unread",
        "owner_notifications",
        ["owner_id", "is_read"],
        postgresql_where=sa.text("is_read = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_owner_notifications_owner_unread", table_name="owner_notifications")
    op.drop_table("owner_notifications")
    op.drop_column("users", "telegram_linked_at")
    op.drop_column("users", "telegram_link_code")
    op.drop_column("users", "telegram_chat_id")
