"""ai_usage_logs.step_kind for per-step cost attribution

Revision ID: c8d9e0f1a2b3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_usage_logs",
        sa.Column(
            "step_kind",
            sa.String(length=32),
            nullable=True,
            comment="e.g. intent_classifier, chat_completion — optional analytics slice",
        ),
    )
    op.create_index(
        "ix_ai_usage_logs_step_kind",
        "ai_usage_logs",
        ["step_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_step_kind", table_name="ai_usage_logs")
    op.drop_column("ai_usage_logs", "step_kind")
