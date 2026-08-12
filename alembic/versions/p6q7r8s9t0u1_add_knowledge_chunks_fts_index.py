"""GIN index on knowledge_chunks full-text vector (simple config)

Revision ID: p6q7r8s9t0u1
Revises: n5o6p7q8r9s0
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "p6q7r8s9t0u1"
down_revision: Union[str, Sequence[str], None] = "n5o6p7q8r9s0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_fts "
        "ON knowledge_chunks USING gin (to_tsvector('simple', content))",
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_content_fts")
