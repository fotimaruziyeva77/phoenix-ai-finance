"""
Orchestrate PDF download, text extraction, chunk persistence, and status updates.

This module is independent of FastAPI; workers or tests call it with an :class:`~sqlalchemy.ext.asyncio.AsyncSession`.
"""

from __future__ import annotations

import asyncio
import uuid
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.error_tracking import capture_exception
from app.integrations.storage import object_storage_from_settings
from app.integrations.storage.base import ObjectNotFoundError, ObjectStorageBackend
from app.integrations.storage.read_object import ObjectTooLargeError, read_object_bytes_bounded
from app.repositories.knowledge_chunk_repository import KnowledgeChunkRepository
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.services.knowledge_pdf_text_extraction import extract_pdf_text_by_page
from app.services.knowledge_text_chunking import build_chunk_specs_from_pages


class KnowledgeFileProcessingOutcome(str, Enum):
    """Result of a single processing attempt."""

    SKIPPED = "skipped"
    READY = "ready"
    FAILED = "failed"


def _truncate_message(message: str, max_len: int) -> str:
    message = (message or "").strip()
    if not message:
        return "Processing failed."
    if len(message) <= max_len:
        return message
    if max_len <= 3:
        return message[:max_len]
    return message[: max_len - 3] + "..."


class KnowledgeFileProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        storage: ObjectStorageBackend | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._storage_override = storage
        self._files = KnowledgeFileRepository(session)
        self._chunks = KnowledgeChunkRepository(session)

    def _storage(self) -> ObjectStorageBackend | None:
        if self._storage_override is not None:
            return self._storage_override
        return object_storage_from_settings(self._settings)

    async def process_file(self, file_id: uuid.UUID) -> KnowledgeFileProcessingOutcome:
        """
        Claim the file, extract text, replace chunks, mark ``ready`` or ``failed``.

        * Idempotent for terminal states: rows already ``ready`` or ``processing`` (by another worker)
          do not get claimed → :attr:`KnowledgeFileProcessingOutcome.SKIPPED`.
        * Retries: ``failed`` or ``uploaded`` can be claimed again; chunks are deleted and re-inserted.
        """
        claimed = await self._files.try_claim_for_processing(file_id)
        if claimed is None:
            return KnowledgeFileProcessingOutcome.SKIPPED

        await self._session.commit()

        oid, bid = claimed.owner_id, claimed.bot_id
        err_max = self._settings.knowledge_processing_error_max_chars
        storage = self._storage()
        if storage is None:
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(
                    "Object storage is not configured.",
                    err_max,
                ),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED

        mime = (claimed.mime_type or "").strip().lower()
        if mime != "application/pdf":
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(
                    f"Unsupported mime type for text extraction: {claimed.mime_type!r}",
                    err_max,
                ),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED

        max_bytes = self._settings.knowledge_pdf_max_upload_bytes
        try:
            pdf_bytes = await read_object_bytes_bounded(
                storage,
                key=claimed.storage_key,
                max_bytes=max_bytes,
            )
        except ObjectNotFoundError as exc:
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(str(exc), err_max),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED
        except ObjectTooLargeError as exc:
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(
                    f"Stored object exceeds configured max_bytes={exc.max_bytes}",
                    err_max,
                ),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED
        except Exception as exc:  # noqa: BLE001 — surface as processing_error
            capture_exception(
                exc,
                domain="knowledge_pdf",
                tags={"file_id": str(file_id), "bot_id": str(bid), "stage": "storage_read"},
            )
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(str(exc), err_max),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED

        try:
            page_count, page_texts = await asyncio.to_thread(extract_pdf_text_by_page, pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            capture_exception(
                exc,
                domain="knowledge_pdf",
                tags={"file_id": str(file_id), "bot_id": str(bid), "stage": "pdf_extract"},
            )
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(str(exc), err_max),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED

        specs = build_chunk_specs_from_pages(
            page_texts,
            max_chars=self._settings.knowledge_chunk_max_chars,
            chars_per_token_estimate=self._settings.ai_token_chars_per_token_estimate,
        )

        try:
            async with self._session.begin():
                await self._chunks.delete_chunks_for_file(
                    file_id,
                    owner_id=oid,
                    bot_id=bid,
                )
                await self._chunks.insert_chunks_for_file(claimed, specs)
                await self._files.mark_processing_ready(
                    file_id,
                    owner_id=oid,
                    bot_id=bid,
                    page_count=page_count,
                )
        except Exception as exc:  # noqa: BLE001
            capture_exception(
                exc,
                domain="knowledge_pdf",
                tags={"file_id": str(file_id), "bot_id": str(bid), "stage": "chunk_persist"},
            )
            await self._files.mark_processing_failed(
                file_id,
                owner_id=oid,
                bot_id=bid,
                message=_truncate_message(str(exc), err_max),
            )
            await self._session.commit()
            return KnowledgeFileProcessingOutcome.FAILED

        return KnowledgeFileProcessingOutcome.READY
