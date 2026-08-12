"""leads: owner delivery tracking; users: lead notify channel prefs

Revision ID: a7b8c9d0e1f2
Revises: f6e5d4c3b2a1
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6e5d4c3b2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TELEGRAM_STATUS_CHECK = (
    "telegram_delivery_status IS NULL OR telegram_delivery_status IN ("
    "'skipped_not_configured', 'skipped_no_target', 'skipped_owner_pref', "
    "'delivered', 'failed')"
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "lead_telegram_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "lead_email_alerts_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "leads",
        sa.Column("owner_inbox_routed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("telegram_delivery_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column(
            "telegram_delivery_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "leads",
        sa.Column("telegram_delivery_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_leads_telegram_delivery_status_allowed",
        "leads",
        _TELEGRAM_STATUS_CHECK,
    )
    op.create_index("ix_leads_owner_inbox_routed_at", "leads", ["owner_inbox_routed_at"])


def downgrade() -> None:
    op.drop_index("ix_leads_owner_inbox_routed_at", table_name="leads")
    op.drop_constraint("ck_leads_telegram_delivery_status_allowed", "leads", type_="check")
    op.drop_column("leads", "telegram_delivery_updated_at")
    op.drop_column("leads", "telegram_delivery_attempts")
    op.drop_column("leads", "telegram_delivery_status")
    op.drop_column("leads", "owner_inbox_routed_at")

    op.drop_column("users", "lead_email_alerts_enabled")
    op.drop_column("users", "lead_telegram_alerts_enabled")
