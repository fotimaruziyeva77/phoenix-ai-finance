"""add ai foundation: conversations, messages, usage logs, daily aggregates

Revision ID: e2f3a4b5c6d7
Revises: d9e1f2a3b4c5
Create Date: 2026-04-02

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e2f3a4b5c6d7"
down_revision = "d9e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
            "status IN ('active','closed')",
            name="ck_conversations_status_allowed",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_bot_id", "conversations", ["bot_id"], unique=False)
    op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("tokens_total", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user','assistant','system')",
            name="ck_messages_role_allowed",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_bot_id", "messages", ["bot_id"], unique=False)
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"], unique=False)
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_usage_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column(
            "tokens_input",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tokens_output",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tokens_total",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column(
            "success",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_logs_bot_id", "ai_usage_logs", ["bot_id"], unique=False)
    op.create_index(
        "ix_ai_usage_logs_conversation_id",
        "ai_usage_logs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index("ix_ai_usage_logs_message_id", "ai_usage_logs", ["message_id"], unique=False)
    op.create_index(
        "ix_ai_usage_logs_bot_id_created_at",
        "ai_usage_logs",
        ["bot_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "daily_ai_usage_aggregates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column(
            "total_requests",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_tokens",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(precision=16, scale=8),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("avg_latency_ms", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "usage_date", name="uq_daily_ai_usage_bot_date"),
    )
    op.create_index(
        "ix_daily_ai_usage_aggregates_bot_id",
        "daily_ai_usage_aggregates",
        ["bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_ai_usage_aggregates_bot_id", table_name="daily_ai_usage_aggregates")
    op.drop_table("daily_ai_usage_aggregates")

    op.drop_index("ix_ai_usage_logs_bot_id_created_at", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_message_id", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_conversation_id", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_bot_id", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")

    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_bot_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_owner_id", table_name="conversations")
    op.drop_index("ix_conversations_bot_id", table_name="conversations")
    op.drop_table("conversations")
