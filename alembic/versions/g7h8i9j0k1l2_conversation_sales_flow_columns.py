"""conversation sales-flow: state, intent, niche snapshot, collected JSON, message timestamps

Revision ID: g7h8i9j0k1l2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "g7h8i9j0k1l2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None

_STATE_IN = (
    "start",
    "qualification",
    "clarification",
    "offer",
    "objection_handling",
    "closing",
    "fallback",
    "completed",
)
_STATE_SQL = ", ".join(f"'{s}'" for s in _STATE_IN)

_INTENT_IN = (
    "greeting",
    "sales_interest",
    "support",
    "faq",
    "consulting",
    "unknown",
)
_INTENT_SQL = ", ".join(f"'{s}'" for s in _INTENT_IN)


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "current_state",
            sa.String(length=32),
            server_default="start",
            nullable=False,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("detected_intent", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("niche_id_snapshot", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "collected_data_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("last_user_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("last_assistant_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_conversations_current_state_allowed",
        "conversations",
        f"current_state IN ({_STATE_SQL})",
    )
    op.create_check_constraint(
        "ck_conversations_detected_intent_allowed",
        "conversations",
        f"(detected_intent IS NULL OR detected_intent IN ({_INTENT_SQL}))",
    )
    op.create_index(
        "ix_conversations_niche_id_snapshot",
        "conversations",
        ["niche_id_snapshot"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_last_user_message_at",
        "conversations",
        ["last_user_message_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_last_user_message_at", table_name="conversations")
    op.drop_index("ix_conversations_niche_id_snapshot", table_name="conversations")
    op.drop_constraint("ck_conversations_detected_intent_allowed", "conversations", type_="check")
    op.drop_constraint("ck_conversations_current_state_allowed", "conversations", type_="check")
    op.drop_column("conversations", "last_assistant_message_at")
    op.drop_column("conversations", "last_user_message_at")
    op.drop_column("conversations", "collected_data_json")
    op.drop_column("conversations", "niche_id_snapshot")
    op.drop_column("conversations", "detected_intent")
    op.drop_column("conversations", "current_state")
