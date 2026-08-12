"""add telegram_configs table (Telegram bot attachment, encrypted token)

Revision ID: u1v2w3x4y5z6
Revises: s0t1u2v3w4
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "s0t1u2v3w4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bot_token_encrypted", sa.Text(), nullable=False),
        sa.Column("bot_username", sa.String(length=64), nullable=True),
        sa.Column("webhook_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "is_connected",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", name="uq_telegram_configs_bot_id"),
    )
    op.create_index("ix_telegram_configs_bot_id", "telegram_configs", ["bot_id"], unique=False)
    op.create_index("ix_telegram_configs_owner_id", "telegram_configs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_telegram_configs_owner_id", table_name="telegram_configs")
    op.drop_index("ix_telegram_configs_bot_id", table_name="telegram_configs")
    op.drop_table("telegram_configs")
