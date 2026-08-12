"""Text segments extracted from a knowledge file for retrieval (no vectors in this module)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_file_id",
            "chunk_index",
            name="uq_knowledge_chunks_file_chunk_index",
        ),
        CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_chunk_index_non_negative"),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 0",
            name="ck_knowledge_chunks_page_number_non_negative",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_knowledge_chunks_token_count_non_negative",
        ),
        Index("ix_knowledge_chunks_bot_id_knowledge_file_id", "bot_id", "knowledge_file_id"),
        Index("ix_knowledge_chunks_owner_id_bot_id", "owner_id", "bot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    knowledge_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    knowledge_file: Mapped["KnowledgeFile"] = relationship(
        "KnowledgeFile",
        back_populates="chunks",
    )
    bot: Mapped["Bot"] = relationship("Bot", back_populates="knowledge_chunks")
    owner: Mapped["User"] = relationship("User", back_populates="knowledge_chunks")
