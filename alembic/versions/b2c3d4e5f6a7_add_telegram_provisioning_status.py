"""telegram_configs: provisioning lifecycle + nullable bot token

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f8
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_configs",
        sa.Column(
            "provisioning_status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.execute(
        """
        UPDATE telegram_configs
        SET provisioning_status = CASE
            WHEN is_connected THEN 'active'
            ELSE 'channel_pending'
        END
        """
    )
    op.alter_column(
        "telegram_configs",
        "provisioning_status",
        server_default=None,
    )
    op.alter_column(
        "telegram_configs",
        "bot_token_encrypted",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM telegram_configs
        WHERE bot_token_encrypted IS NULL OR trim(bot_token_encrypted) = ''
        """
    )
    op.alter_column(
        "telegram_configs",
        "bot_token_encrypted",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.drop_column("telegram_configs", "provisioning_status")
