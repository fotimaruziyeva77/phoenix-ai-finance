"""add bot ai settings columns

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-04-02

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bots",
        sa.Column(
            "provider_name",
            sa.String(length=64),
            server_default="gemini",
            nullable=False,
        ),
    )
    op.add_column("bots", sa.Column("model_name", sa.String(length=128), nullable=True))
    op.add_column("bots", sa.Column("temperature", sa.Float(), nullable=True))
    op.add_column("bots", sa.Column("max_output_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("bots", "max_output_tokens")
    op.drop_column("bots", "temperature")
    op.drop_column("bots", "model_name")
    op.drop_column("bots", "provider_name")
