from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import BillingServiceDep, BotKnowledgeFileServiceDep, CurrentUser, DbSession, rate_limit_knowledge_upload
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.schemas.knowledge_file import (
    KnowledgeFileIngestionJobStatus,
    KnowledgeFileListResponse,
    KnowledgeFilePublicRead,
)

router = APIRouter(tags=["bot knowledge"])


@router.post(
    "/bots/{bot_id}/knowledge/files",
    response_model=KnowledgeFilePublicRead,
    status_code=201,
    summary="Upload a PDF knowledge file for a bot",
)
async def upload_bot_knowledge_pdf(
    bot_id: UUID,
    user: CurrentUser,
    _: Annotated[None, Depends(rate_limit_knowledge_upload)],
    session: DbSession,
    service: BotKnowledgeFileServiceDep,
    billing_service: BillingServiceDep,
    file: UploadFile = File(..., description="PDF document (Content-Type: application/pdf)"),
) -> KnowledgeFilePublicRead:
    # Enforce plan PDF file count limit before accepting the upload
    existing = await service.list_knowledge_files_for_bot(user, bot_id)
    await billing_service.enforce_pdf_limit(user, len(existing.items))

    # Enforce plan storage limit (sum of all knowledge file bytes for this owner)
    k_repo = KnowledgeFileRepository(session)
    total_bytes = await k_repo.get_total_storage_bytes_for_owner(user.id)
    total_mb = total_bytes / (1024 * 1024)
    await billing_service.enforce_storage_limit(user, total_mb)

    return await service.upload_pdf_knowledge_file(user, bot_id, file)


@router.get(
    "/bots/{bot_id}/knowledge/files",
    response_model=KnowledgeFileListResponse,
    summary="List knowledge files for a bot",
)
async def list_bot_knowledge_files(
    bot_id: UUID,
    user: CurrentUser,
    service: BotKnowledgeFileServiceDep,
) -> KnowledgeFileListResponse:
    return await service.list_knowledge_files_for_bot(user, bot_id)


@router.get(
    "/bots/{bot_id}/knowledge/files/{file_id}/ingestion",
    response_model=KnowledgeFileIngestionJobStatus,
    summary="Knowledge PDF ingestion job status (async pipeline)",
)
async def get_bot_knowledge_file_ingestion_status(
    bot_id: UUID,
    file_id: UUID,
    user: CurrentUser,
    service: BotKnowledgeFileServiceDep,
) -> KnowledgeFileIngestionJobStatus:
    return await service.get_knowledge_ingestion_job_status(user, bot_id, file_id)
