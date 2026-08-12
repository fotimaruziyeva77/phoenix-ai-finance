"""Platform moderation columns (user/bot suspension metadata + audit metadata).

Revision ID: z9y8x7w6v5u4
Revises: w9x0y1z2a3b4
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z9y8x7w6v5u4"
down_revision: Union[str, Sequence[str], None] = "w9x0y1z2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("suspension_reason", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "bots",
        sa.Column("platform_suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "bots",
        sa.Column("platform_suspension_reason", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "metadata_json")
    op.drop_column("bots", "platform_suspension_reason")
    op.drop_column("bots", "platform_suspended_at")
    op.drop_column("users", "suspension_reason")
    op.drop_column("users", "suspended_at")
