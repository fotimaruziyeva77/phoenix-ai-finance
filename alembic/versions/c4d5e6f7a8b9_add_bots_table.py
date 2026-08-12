"""add bots table

Revision ID: c4d5e6f7a8b9
Revises: b3e4f5a6c7d9
Create Date: 2026-03-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3e4f5a6c7d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("niche_id", sa.String(length=120), nullable=False),
        sa.Column("goal_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("welcome_message", sa.String(length=1024), nullable=True),
        sa.Column("tone", sa.String(length=120), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("short_description", sa.String(length=300), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('draft','active','paused','archived')",
            name="ck_bots_status_allowed",
        ),
        sa.CheckConstraint(
            "goal_type IN ('support','sales','faq','consulting')",
            name="ck_bots_goal_type_allowed",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bots_owner_id", "bots", ["owner_id"], unique=False)
    op.create_index("ix_bots_status", "bots", ["status"], unique=False)
    op.create_index("ix_bots_owner_id_updated_at", "bots", ["owner_id", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bots_owner_id_updated_at", table_name="bots")
    op.drop_index("ix_bots_status", table_name="bots")
    op.drop_index("ix_bots_owner_id", table_name="bots")
    op.drop_table("bots")
