"""Add target_user_ids to feature_flags table.

Revision ID: ff_target_users_001
Revises: h8c9d1e2f3g4
Create Date: 2026-06-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ff_target_users_001"
down_revision = "h8c9d1e2f3g4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feature_flags",
        sa.Column(
            "target_user_ids",
            sa.Text(),
            nullable=True,
            comment="JSON array of user UUIDs to target. NULL = no user-level targeting.",
        ),
    )


def downgrade() -> None:
    op.drop_column("feature_flags", "target_user_ids")
