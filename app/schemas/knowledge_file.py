"""Pydantic shapes for bot-attached knowledge files (upload + status; no extraction payloads yet)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge_file import KnowledgeFile

KnowledgeFileProcessingStatusLiteral = Literal["uploaded", "processing", "ready", "failed", "dead_letter"]

KnowledgeIngestionJobStatusLiteral = Literal["pending", "processing", "completed", "failed", "dead_letter"]


class KnowledgeFileRead(BaseModel):
    """Full row for detail views and admin tooling."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    original_filename: str = Field(..., max_length=512)
    storage_key: str = Field(..., max_length=1024)
    mime_type: str = Field(..., max_length=255)
    file_size_bytes: int = Field(..., ge=0)
    processing_status: KnowledgeFileProcessingStatusLiteral
    processing_error: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    ingestion_failure_count: int = Field(default=0, ge=0)
    uploaded_at: datetime
    updated_at: datetime


class KnowledgeFileListItem(BaseModel):
    """Table and picker projection (no storage_key)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    original_filename: str = Field(..., max_length=512)
    mime_type: str = Field(..., max_length=255)
    file_size_bytes: int = Field(..., ge=0)
    processing_status: KnowledgeFileProcessingStatusLiteral
    processing_error: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    ingestion_failure_count: int = Field(default=0, ge=0)
    uploaded_at: datetime
    updated_at: datetime


class KnowledgeFileUploadResponse(BaseModel):
    """Immediate response after accepting an upload (processing is asynchronous)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    original_filename: str = Field(..., max_length=512)
    processing_status: KnowledgeFileProcessingStatusLiteral
    uploaded_at: datetime


class KnowledgeFilePublicRead(BaseModel):
    """API response without internal ``storage_key``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bot_id: UUID
    owner_id: UUID
    original_filename: str = Field(..., max_length=512)
    mime_type: str = Field(..., max_length=255)
    file_size_bytes: int = Field(..., ge=0)
    processing_status: KnowledgeFileProcessingStatusLiteral
    processing_error: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    ingestion_failure_count: int = Field(default=0, ge=0)
    uploaded_at: datetime
    updated_at: datetime


class KnowledgeFileIngestionJobStatus(BaseModel):
    """Normalized ingestion lifecycle for dashboards (maps DB ``processing_status``)."""

    file_id: UUID
    bot_id: UUID
    status: KnowledgeIngestionJobStatusLiteral
    processing_status: KnowledgeFileProcessingStatusLiteral
    ingestion_failure_count: int = Field(..., ge=0)
    processing_error: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    searchable: bool = Field(
        description="True only when chunks exist and FTS retrieval includes this file.",
    )
    updated_at: datetime


class KnowledgeFileListResponse(BaseModel):
    items: list[KnowledgeFileListItem]
    total: int = Field(..., ge=0)


class KnowledgeFileStatusUpdate(BaseModel):
    """Service/worker payload to advance pipeline state (internal)."""

    model_config = ConfigDict(extra="forbid")

    processing_status: KnowledgeFileProcessingStatusLiteral
    processing_error: str | None = None
    page_count: int | None = Field(default=None, ge=0)


def knowledge_ingestion_job_status_from_row(row: KnowledgeFile) -> KnowledgeFileIngestionJobStatus:
    raw = row.processing_status
    if raw == "uploaded":
        lifecycle: KnowledgeIngestionJobStatusLiteral = "pending"
    elif raw == "processing":
        lifecycle = "processing"
    elif raw == "ready":
        lifecycle = "completed"
    elif raw == "failed":
        lifecycle = "failed"
    elif raw == "dead_letter":
        lifecycle = "dead_letter"
    else:
        lifecycle = "failed"
    return KnowledgeFileIngestionJobStatus(
        file_id=row.id,
        bot_id=row.bot_id,
        status=lifecycle,
        processing_status=raw,
        ingestion_failure_count=int(row.ingestion_failure_count),
        processing_error=row.processing_error,
        page_count=row.page_count,
        searchable=(raw == "ready"),
        updated_at=row.updated_at,
    )
