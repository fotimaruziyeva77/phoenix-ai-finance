"""add leads table (owner-scoped CRM pipeline foundation)

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-04-03

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("niche_id", sa.String(length=120), nullable=False),
        sa.Column("lead_score", sa.Integer(), nullable=True),
        sa.Column("lead_temperature", sa.String(length=16), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'new'"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_channel", sa.String(length=64), nullable=True),
        sa.Column("collected_data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "status IN ('new','contacted','qualified','proposal','won','lost')",
            name="ck_leads_status_allowed",
        ),
        sa.CheckConstraint(
            "lead_temperature IS NULL OR lead_temperature IN ('cold','warm','hot')",
            name="ck_leads_temperature_allowed",
        ),
        sa.CheckConstraint(
            "lead_score IS NULL OR (lead_score >= 0 AND lead_score <= 100)",
            name="ck_leads_score_range",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_bot_id", "leads", ["bot_id"], unique=False)
    op.create_index("ix_leads_owner_id", "leads", ["owner_id"], unique=False)
    op.create_index("ix_leads_conversation_id", "leads", ["conversation_id"], unique=False)
    op.create_index("ix_leads_niche_id", "leads", ["niche_id"], unique=False)
    op.create_index("ix_leads_status", "leads", ["status"], unique=False)
    op.create_index(
        "ix_leads_owner_id_created_at",
        "leads",
        ["owner_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_owner_id_created_at", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_niche_id", table_name="leads")
    op.drop_index("ix_leads_conversation_id", table_name="leads")
    op.drop_index("ix_leads_owner_id", table_name="leads")
    op.drop_index("ix_leads_bot_id", table_name="leads")
    op.drop_table("leads")
