"""widget_configs: pre_chat_form_json + custom_css columns

Revision ID: e5f6a7b8c9d1
Revises: d4e5f6a7b8c0
Create Date: 2026-05-30

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "widget_configs",
        sa.Column(
            "pre_chat_form_json",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            comment='Pre-chat form fields, e.g. [{"name":"name","label":"Name","type":"text","required":true}].',
        ),
    )
    op.add_column(
        "widget_configs",
        sa.Column(
            "custom_css",
            sa.String(8192),
            nullable=True,
            comment="Owner-provided CSS injected into the widget iframe (max 8 KB).",
        ),
    )


def downgrade() -> None:
    op.drop_column("widget_configs", "custom_css")
    op.drop_column("widget_configs", "pre_chat_form_json")
