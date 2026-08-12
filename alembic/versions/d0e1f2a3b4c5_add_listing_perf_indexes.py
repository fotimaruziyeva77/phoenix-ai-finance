"""B-tree indexes for hot list/sort paths (leads CRM, admin users/bots).

Revision ID: d0e1f2a3b4c5
Revises: c8d9e0f1a2b3
Create Date: 2026-04-09

- ``leads``: owner inbox sorts by ``updated_at`` (see ``LeadRepository.list_leads_for_owner``);
  existing ``ix_leads_owner_id_created_at`` does not match that ORDER BY.
- ``users``: superadmin list orders by ``created_at`` (``PlatformAdminRepository.list_users_with_counts``).
- ``bots``: superadmin bot list orders by ``updated_at`` globally; existing index is per-owner only.

Validate with ``EXPLAIN (ANALYZE, BUFFERS)`` on staging before/after migration.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_leads_owner_id_updated_at",
        "leads",
        ["owner_id", "updated_at"],
        unique=False,
        postgresql_ops={"updated_at": "DESC NULLS LAST"},
    )
    op.create_index(
        "ix_users_created_at",
        "users",
        ["created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC NULLS LAST"},
    )
    op.create_index(
        "ix_bots_updated_at",
        "bots",
        ["updated_at"],
        unique=False,
        postgresql_ops={"updated_at": "DESC NULLS LAST"},
    )


def downgrade() -> None:
    op.drop_index("ix_bots_updated_at", table_name="bots")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_leads_owner_id_updated_at", table_name="leads")
