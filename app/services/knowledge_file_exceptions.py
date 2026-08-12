from __future__ import annotations

from typing import Any, ClassVar


class KnowledgeFileServiceError(Exception):
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "knowledge_file_error"
    default_message: ClassVar[str] = "Knowledge file operation failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class KnowledgeFileValidationError(KnowledgeFileServiceError):
    status_code = 422
    code = "knowledge_file_validation_error"
    default_message = "Knowledge file upload is invalid"


class KnowledgeFileStorageNotConfiguredError(KnowledgeFileServiceError):
    status_code = 503
    code = "knowledge_storage_not_configured"
    default_message = "File storage is not configured"


class KnowledgeFileStorageUploadError(KnowledgeFileServiceError):
    status_code = 503
    code = "knowledge_storage_upload_failed"
    default_message = "Could not store the file"


class KnowledgeFilePersistenceError(KnowledgeFileServiceError):
    status_code = 500
    code = "knowledge_file_persistence_error"
    default_message = "Could not save file metadata"


class KnowledgeFileNotFoundError(KnowledgeFileServiceError):
    status_code = 404
    code = "knowledge_file_not_found"
    default_message = "Knowledge file not found"
