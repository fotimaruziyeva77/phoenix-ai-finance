"""conversations: web_widget visitor session columns + partial unique index

Revision ID: s0t1u2v3w4
Revises: q7r8s9t0u1v2
Create Date: 2026-04-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s0t1u2v3w4"
down_revision: Union[str, Sequence[str], None] = "q7r8s9t0u1v2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("public_visitor_session_key", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("visitor_client_hint", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_conversations_public_visitor_session_key",
        "conversations",
        ["public_visitor_session_key"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_conversations_web_widget_requires_visitor_key",
        "conversations",
        "(channel IS DISTINCT FROM 'web_widget') OR (public_visitor_session_key IS NOT NULL)",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_conversations_bot_web_widget_visitor_session_key "
        "ON conversations (bot_id, public_visitor_session_key) "
        "WHERE channel = 'web_widget' AND public_visitor_session_key IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_conversations_bot_web_widget_visitor_session_key")
    op.drop_constraint(
        "ck_conversations_web_widget_requires_visitor_key",
        "conversations",
        type_="check",
    )
    op.drop_index("ix_conversations_public_visitor_session_key", table_name="conversations")
    op.drop_column("conversations", "visitor_client_hint")
    op.drop_column("conversations", "public_visitor_session_key")
