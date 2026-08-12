"""add telegram_configs.webhook_secret_token_encrypted for Bot API secret_token

Revision ID: v8w9x0y1z2a3
Revises: u1v2w3x4y5z6
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v8w9x0y1z2a3"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_configs",
        sa.Column(
            "webhook_secret_token_encrypted",
            sa.Text(),
            nullable=True,
            comment="Fernet ciphertext of Telegram setWebhook secret_token (X-Telegram-Bot-Api-Secret-Token).",
        ),
    )


def downgrade() -> None:
    op.drop_column("telegram_configs", "webhook_secret_token_encrypted")
