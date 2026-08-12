"""add knowledge_files table (bot-attached uploads)

Revision ID: m4n5o6p7q8r9
Revises: j0k1l2m3n4o5
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, Sequence[str], None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=32),
            server_default=sa.text("'uploaded'"),
            nullable=False,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at",
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
            "processing_status IN ('uploaded','processing','ready','failed')",
            name="ck_knowledge_files_processing_status_allowed",
        ),
        sa.CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_knowledge_files_size_non_negative",
        ),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="ck_knowledge_files_page_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_knowledge_files_storage_key"),
    )
    op.create_index("ix_knowledge_files_bot_id", "knowledge_files", ["bot_id"], unique=False)
    op.create_index("ix_knowledge_files_owner_id", "knowledge_files", ["owner_id"], unique=False)
    op.create_index(
        "ix_knowledge_files_bot_id_uploaded_at",
        "knowledge_files",
        ["bot_id", "uploaded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_files_bot_id_uploaded_at", table_name="knowledge_files")
    op.drop_index("ix_knowledge_files_owner_id", table_name="knowledge_files")
    op.drop_index("ix_knowledge_files_bot_id", table_name="knowledge_files")
    op.drop_table("knowledge_files")
