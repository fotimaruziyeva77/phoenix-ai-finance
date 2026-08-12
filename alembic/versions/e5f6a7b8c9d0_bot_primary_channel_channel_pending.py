"""bots: primary_channel + channel_pending lifecycle status

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c0
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_bots_status_allowed", "bots", type_="check")
    op.create_check_constraint(
        "ck_bots_status_allowed",
        "bots",
        "status IN ('draft','active','paused','archived','channel_pending')",
    )
    op.add_column("bots", sa.Column("primary_channel", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "ck_bots_primary_channel_allowed",
        "bots",
        "primary_channel IS NULL OR primary_channel IN ('web','telegram','both')",
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE bots SET status = 'draft' WHERE status = 'channel_pending'"),
    )
    op.drop_constraint("ck_bots_primary_channel_allowed", "bots", type_="check")
    op.drop_column("bots", "primary_channel")
    op.drop_constraint("ck_bots_status_allowed", "bots", type_="check")
    op.create_check_constraint(
        "ck_bots_status_allowed",
        "bots",
        "status IN ('draft','active','paused','archived')",
    )
