"""Add feature_flags (IF NOT EXISTS), support_tickets, and coupons tables.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-18

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    # ── feature_flags (may already exist — created manually in prod) ─────────
    if "feature_flags" not in existing_tables:
        op.create_table(
            "feature_flags",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("target_plan", sa.String(length=32), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("key", name="uq_feature_flags_key"),
        )
        op.create_index("ix_feature_flags_key", "feature_flags", ["key"], unique=True)

    # ── support_tickets ───────────────────────────────────────────────────────
    if "support_tickets" not in existing_tables:
        op.create_table(
            "support_tickets",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("subject", sa.String(length=256), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(length=8), nullable=False, server_default="normal"),
            sa.Column("admin_note", sa.Text(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_support_tickets_user_id",    "support_tickets", ["user_id"])
        op.create_index("ix_support_tickets_status",     "support_tickets", ["status"])
        op.create_index("ix_support_tickets_created_at", "support_tickets", ["created_at"])

    # ── coupons ───────────────────────────────────────────────────────────────
    if "coupons" not in existing_tables:
        op.create_table(
            "coupons",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("discount_type", sa.String(length=8), nullable=False),
            sa.Column("discount_value", sa.Numeric(10, 2), nullable=False),
            sa.Column("target_plan", sa.String(length=32), nullable=True),
            sa.Column("max_uses", sa.Integer(), nullable=True),
            sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("code", name="uq_coupons_code"),
        )
        op.create_index("ix_coupons_code", "coupons", ["code"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if "coupons" in existing_tables:
        op.drop_index("ix_coupons_code", table_name="coupons")
        op.drop_table("coupons")

    if "support_tickets" in existing_tables:
        op.drop_index("ix_support_tickets_created_at", table_name="support_tickets")
        op.drop_index("ix_support_tickets_status",     table_name="support_tickets")
        op.drop_index("ix_support_tickets_user_id",    table_name="support_tickets")
        op.drop_table("support_tickets")

    if "feature_flags" in existing_tables:
        op.drop_index("ix_feature_flags_key", table_name="feature_flags")
        op.drop_table("feature_flags")
