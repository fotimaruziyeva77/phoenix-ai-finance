"""
Uploaded knowledge files attached to a bot (storage metadata + processing state).

``owner_id`` mirrors the bot owner for owner-scoped queries without always joining ``bots``.
Callers should keep ``owner_id`` aligned with ``bot.owner_id`` on insert/update.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

_CHECK_KNOWLEDGE_FILE_PROCESSING_STATUS = (
    "processing_status IN ('uploaded','processing','ready','failed','dead_letter')"
)


class KnowledgeFile(Base):
    """Bot-scoped knowledge document: blob metadata, processing lifecycle, and chunk parent for FTS retrieval."""

    __tablename__ = "knowledge_files"
    __table_args__ = (
        CheckConstraint(
            _CHECK_KNOWLEDGE_FILE_PROCESSING_STATUS,
            name="ck_knowledge_files_processing_status_allowed",
        ),
        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_knowledge_files_size_non_negative",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="ck_knowledge_files_page_count_non_negative",
        ),
        CheckConstraint(
            "ingestion_failure_count >= 0",
            name="ck_knowledge_files_ingestion_failure_count_non_negative",
        ),
        Index(
            "ix_knowledge_files_bot_id_uploaded_at",
            "bot_id",
            "uploaded_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        unique=True,
        comment="Opaque object key in blob storage (S3-compatible, etc.).",
    )
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
        server_default="uploaded",
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingestion_failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bot: Mapped["Bot"] = relationship("Bot", back_populates="knowledge_files")
    owner: Mapped["User"] = relationship("User", back_populates="knowledge_files")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="knowledge_file",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="KnowledgeChunk.chunk_index",
    )
