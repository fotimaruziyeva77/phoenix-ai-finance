"""Enable pg_trgm extension and add GIN trigram index on knowledge_chunks.content

Revision ID: f6a7b8c9d1e2
Revises: e5f6a7b8c9d1
Create Date: 2026-05-30

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "f6a7b8c9d1e2"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_trgm "
        "ON knowledge_chunks USING gin (content gin_trgm_ops);",
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_content_trgm;")
    # Intentionally not dropping the pg_trgm extension -- other objects may depend on it.
