"""add knowledge_chunks table (extracted text segments per knowledge file)

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-04-05

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n5o6p7q8r9s0"
down_revision: Union[str, Sequence[str], None] = "m4n5o6p7q8r9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("knowledge_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_chunk_index_non_negative"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 0",
            name="ck_knowledge_chunks_page_number_non_negative",
        ),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_knowledge_chunks_token_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_file_id"], ["knowledge_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_file_id",
            "chunk_index",
            name="uq_knowledge_chunks_file_chunk_index",
        ),
    )
    op.create_index("ix_knowledge_chunks_bot_id", "knowledge_chunks", ["bot_id"], unique=False)
    op.create_index("ix_knowledge_chunks_owner_id", "knowledge_chunks", ["owner_id"], unique=False)
    op.create_index(
        "ix_knowledge_chunks_bot_id_knowledge_file_id",
        "knowledge_chunks",
        ["bot_id", "knowledge_file_id"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_chunks_owner_id_bot_id",
        "knowledge_chunks",
        ["owner_id", "bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_owner_id_bot_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_bot_id_knowledge_file_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_owner_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_bot_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
