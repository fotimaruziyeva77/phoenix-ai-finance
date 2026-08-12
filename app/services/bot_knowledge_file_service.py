from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.datastructures import UploadFile

from app.core.config import Settings
from app.core.knowledge_ingestion_queue import schedule_knowledge_file_ingestion
from app.core.logging import get_logger
from app.integrations.storage import knowledge_file_object_key, object_storage_from_settings
from app.integrations.storage.base import ObjectStorageError
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.schemas.knowledge_file import (
    KnowledgeFileIngestionJobStatus,
    KnowledgeFileListItem,
    KnowledgeFileListResponse,
    KnowledgeFilePublicRead,
    knowledge_ingestion_job_status_from_row,
)
from app.services.bot_exceptions import BotNotFoundError
from app.services.knowledge_file_exceptions import (
    KnowledgeFileNotFoundError,
    KnowledgeFilePersistenceError,
    KnowledgeFileStorageNotConfiguredError,
    KnowledgeFileStorageUploadError,
    KnowledgeFileValidationError,
)
from app.services.knowledge_upload_safety import note_upload_validation_rejected

_ALLOWED_PDF_CONTENT_TYPES = frozenset({"application/pdf"})
# Browsers and CLI tools often send ``application/octet-stream`` for PDFs; magic bytes still required.
_ALLOWED_UPLOAD_CONTENT_TYPES = _ALLOWED_PDF_CONTENT_TYPES | frozenset({"application/octet-stream"})
_READ_CHUNK = 1024 * 1024
_LOG = get_logger("bot_knowledge_file_service")


def _declared_type_allowed(content_type: str | None) -> bool:
    c = (content_type or "").strip().lower()
    if c == "":
        return True
    return c in _ALLOWED_UPLOAD_CONTENT_TYPES


def _enforce_pdf_magic_after_read(raw: bytes, *, scan_bytes: int) -> None:
    """Reject obvious non-PDFs and PE-polyglots; require ``%PDF`` in the leading scan window."""
    if raw.startswith(b"MZ"):
        raise KnowledgeFileValidationError(
            "This file is not accepted as a PDF.",
            details={"field": "file", "reason": "executable_prefix"},
        )
    window = raw[: min(scan_bytes, len(raw))]
    if b"%PDF" not in window:
        raise KnowledgeFileValidationError(
            "The uploaded file does not contain a PDF signature in the leading bytes.",
            details={"field": "file", "reason": "invalid_pdf_magic"},
        )


class BotKnowledgeFileService:
    def __init__(
        self,
        bot_repo: BotRepository,
        file_repo: KnowledgeFileRepository,
        settings: Settings,
    ) -> None:
        self._bots = bot_repo
        self._files = file_repo
        self._settings = settings

    async def _reject_validation(
        self,
        current_user: User,
        bot_id: uuid.UUID,
        *,
        log_reason: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        await note_upload_validation_rejected(
            owner_id=current_user.id,
            bot_id=bot_id,
            reason=log_reason,
            settings=self._settings,
        )
        raise KnowledgeFileValidationError(message, details=details)

    async def upload_pdf_knowledge_file(
        self,
        current_user: User,
        bot_id: uuid.UUID,
        upload: UploadFile,
    ) -> KnowledgeFilePublicRead:
        if not await self._bots.exists_for_owner(owner_id=current_user.id, bot_id=bot_id):
            raise BotNotFoundError()

        n_existing = await self._files.count_knowledge_files_for_bot(
            owner_id=current_user.id,
            bot_id=bot_id,
        )
        if n_existing >= self._settings.knowledge_max_files_per_bot:
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="max_files_per_bot",
                message=(
                    f"Maximum number of knowledge files ({self._settings.knowledge_max_files_per_bot}) "
                    "reached for this bot. Remove or replace files before uploading more."
                ),
                details={
                    "field": "file",
                    "reason": "max_files_per_bot",
                    "max_files": self._settings.knowledge_max_files_per_bot,
                },
            )

        raw_name = (upload.filename or "").strip()
        if not raw_name:
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="missing_filename",
                message="A file name is required.",
                details={"field": "file", "reason": "missing_filename"},
            )

        safe_name = PurePosixPath(raw_name).name
        if len(safe_name) > 512:
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="filename_too_long",
                message="File name is too long (max 512 characters).",
                details={"field": "file", "reason": "filename_too_long"},
            )

        if not safe_name.lower().endswith(".pdf"):
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="invalid_extension",
                message="Only PDF files are allowed. The file name must end with .pdf.",
                details={"field": "file", "reason": "invalid_extension"},
            )

        if not _declared_type_allowed(upload.content_type):
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="invalid_content_type",
                message="Only PDF uploads are allowed. Use Content-Type application/pdf or application/octet-stream.",
                details={
                    "field": "file",
                    "reason": "invalid_content_type",
                    "received": upload.content_type,
                },
            )

        max_bytes = self._settings.knowledge_pdf_max_upload_bytes
        chunks: list[bytes] = []
        total = 0
        while True:
            piece = await upload.read(_READ_CHUNK)
            if not piece:
                break
            total += len(piece)
            if total > max_bytes:
                await note_upload_validation_rejected(
                    owner_id=current_user.id,
                    bot_id=bot_id,
                    reason="file_too_large",
                    settings=self._settings,
                )
                _LOG.warning(
                    "knowledge_upload_rejected_large",
                    owner_id=str(current_user.id),
                    bot_id=str(bot_id),
                    max_bytes=max_bytes,
                    declared_bytes=total,
                )
                raise KnowledgeFileValidationError(
                    f"File is too large. Maximum size is {max_bytes} bytes.",
                    details={"field": "file", "reason": "file_too_large", "max_bytes": max_bytes},
                )
            chunks.append(piece)

        raw = b"".join(chunks)
        if len(raw) == 0:
            await self._reject_validation(
                current_user,
                bot_id,
                log_reason="empty_file",
                message="Empty file is not allowed.",
                details={"field": "file", "reason": "empty_file"},
            )

        try:
            _enforce_pdf_magic_after_read(
                raw,
                scan_bytes=self._settings.knowledge_pdf_magic_scan_bytes,
            )
        except KnowledgeFileValidationError as exc:
            details = getattr(exc, "details", None)
            reason = (details or {}).get("reason", "invalid_pdf_magic")
            await note_upload_validation_rejected(
                owner_id=current_user.id,
                bot_id=bot_id,
                reason=str(reason),
                settings=self._settings,
            )
            raise

        storage = object_storage_from_settings(self._settings)
        if storage is None:
            raise KnowledgeFileStorageNotConfiguredError(
                "Configure object storage (bucket and credentials) to upload knowledge files.",
            )

        file_id = uuid.uuid4()
        storage_key = knowledge_file_object_key(
            owner_id=current_user.id,
            bot_id=bot_id,
            file_id=file_id,
            original_filename=safe_name,
        )

        try:
            await storage.upload_file(
                key=storage_key,
                body=raw,
                content_type="application/pdf",
                content_length=len(raw),
            )
        except ObjectStorageError as exc:
            raise KnowledgeFileStorageUploadError(
                "The file could not be stored. Please try again later.",
            ) from exc

        try:
            row = await self._files.create_knowledge_file(
                file_id=file_id,
                bot_id=bot_id,
                owner_id=current_user.id,
                original_filename=safe_name,
                storage_key=storage_key,
                mime_type="application/pdf",
                file_size_bytes=len(raw),
                processing_status="uploaded",
            )
            await self._files.commit()
        except IntegrityError as exc:
            await self._files.rollback()
            try:
                await storage.delete_file(key=storage_key)
            except ObjectStorageError:
                pass
            raise KnowledgeFilePersistenceError() from exc
        except SQLAlchemyError as exc:
            await self._files.rollback()
            try:
                await storage.delete_file(key=storage_key)
            except ObjectStorageError:
                pass
            raise KnowledgeFilePersistenceError() from exc

        await schedule_knowledge_file_ingestion(self._settings, file_id)
        return KnowledgeFilePublicRead.model_validate(row)

    async def get_knowledge_ingestion_job_status(
        self,
        current_user: User,
        bot_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> KnowledgeFileIngestionJobStatus:
        if not await self._bots.exists_for_owner(owner_id=current_user.id, bot_id=bot_id):
            raise BotNotFoundError()
        row = await self._files.get_by_id_for_bot_owner(
            file_id,
            owner_id=current_user.id,
            bot_id=bot_id,
        )
        if row is None:
            raise KnowledgeFileNotFoundError()
        return knowledge_ingestion_job_status_from_row(row)

    async def list_knowledge_files_for_bot(
        self,
        current_user: User,
        bot_id: uuid.UUID,
    ) -> KnowledgeFileListResponse:
        if not await self._bots.exists_for_owner(owner_id=current_user.id, bot_id=bot_id):
            raise BotNotFoundError()

        rows = await self._files.list_knowledge_files_for_bot(
            owner_id=current_user.id,
            bot_id=bot_id,
        )
        total = await self._files.count_knowledge_files_for_bot(
            owner_id=current_user.id,
            bot_id=bot_id,
        )
        items = [KnowledgeFileListItem.model_validate(r) for r in rows]
        return KnowledgeFileListResponse(items=items, total=total)
