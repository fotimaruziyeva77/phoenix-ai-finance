"""lead_events append-only timeline + leads.assignee_user_id

Revision ID: f6e5d4c3b2a1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f6e5d4c3b2a1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("assignee_user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_leads_assignee_user_id", "leads", ["assignee_user_id"])
    op.create_foreign_key(
        "fk_leads_assignee_user_id_users",
        "leads",
        "users",
        ["assignee_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "lead_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ("
            "'lead_created', 'lead_status_changed', 'lead_assigned', 'lead_reassigned', "
            "'note_added', 'notification_delivered', 'notification_failed', "
            "'lead_viewed', 'system_action')",
            name="ck_lead_events_event_type_allowed",
        ),
        sa.CheckConstraint(
            "actor_type IN ('user', 'system', 'integration')",
            name="ck_lead_events_actor_type_allowed",
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_events_lead_id_created_at", "lead_events", ["lead_id", "created_at"])
    op.create_index("ix_lead_events_created_at", "lead_events", ["created_at"])

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION forbid_lead_events_mutation() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION 'lead_events is append-only';
            END;
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER lead_events_append_only_u
            BEFORE UPDATE ON lead_events
            FOR EACH ROW EXECUTE PROCEDURE forbid_lead_events_mutation();
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER lead_events_append_only_d
            BEFORE DELETE ON lead_events
            FOR EACH ROW EXECUTE PROCEDURE forbid_lead_events_mutation();
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS lead_events_append_only_d ON lead_events"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS lead_events_append_only_u ON lead_events"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS forbid_lead_events_mutation()"))

    op.drop_index("ix_lead_events_created_at", table_name="lead_events")
    op.drop_index("ix_lead_events_lead_id_created_at", table_name="lead_events")
    op.drop_table("lead_events")

    op.drop_constraint("fk_leads_assignee_user_id_users", "leads", type_="foreignkey")
    op.drop_index("ix_leads_assignee_user_id", table_name="leads")
    op.drop_column("leads", "assignee_user_id")
