"""knowledge_files: ingestion_failure_count + dead_letter status

Revision ID: d4e5f6a7b8c0
Revises: b2c3d4e5f6a7
Create Date: 2026-04-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_files_processing_status_allowed",
        "knowledge_files",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_files_processing_status_allowed",
        "knowledge_files",
        "processing_status IN ('uploaded','processing','ready','failed','dead_letter')",
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "ingestion_failure_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_knowledge_files_ingestion_failure_count_non_negative",
        "knowledge_files",
        "ingestion_failure_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_knowledge_files_ingestion_failure_count_non_negative",
        "knowledge_files",
        type_="check",
    )
    op.drop_column("knowledge_files", "ingestion_failure_count")
    op.drop_constraint(
        "ck_knowledge_files_processing_status_allowed",
        "knowledge_files",
        type_="check",
    )
    op.create_check_constraint(
        "ck_knowledge_files_processing_status_allowed",
        "knowledge_files",
        "processing_status IN ('uploaded','processing','ready','failed')",
    )
