"""conversations.telegram_chat_id for Telegram channel threading

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w9x0y1z2a3b4"
down_revision: Union[str, Sequence[str], None] = "v8w9x0y1z2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "telegram_chat_id",
            sa.BigInteger(),
            nullable=True,
            comment="Telegram chat id for channel=telegram (private/group); threads multi-turn.",
        ),
    )
    op.create_check_constraint(
        "ck_conversations_telegram_requires_chat_id",
        "conversations",
        "(channel IS DISTINCT FROM 'telegram') OR (telegram_chat_id IS NOT NULL)",
    )
    op.create_index(
        "ix_conversations_telegram_active_unique",
        "conversations",
        ["bot_id", "telegram_chat_id"],
        unique=True,
        postgresql_where=sa.text(
            "channel = 'telegram' AND status = 'active' AND telegram_chat_id IS NOT NULL",
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversations_telegram_active_unique",
        table_name="conversations",
        postgresql_where=sa.text(
            "channel = 'telegram' AND status = 'active' AND telegram_chat_id IS NOT NULL",
        ),
    )
    op.drop_constraint("ck_conversations_telegram_requires_chat_id", "conversations", type_="check")
    op.drop_column("conversations", "telegram_chat_id")
