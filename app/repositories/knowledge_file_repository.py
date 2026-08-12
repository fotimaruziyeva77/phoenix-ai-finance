from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_file import KnowledgeFile


class KnowledgeFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_knowledge_file(
        self,
        *,
        file_id: uuid.UUID,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
        original_filename: str,
        storage_key: str,
        mime_type: str,
        file_size_bytes: int,
        processing_status: str = "uploaded",
    ) -> KnowledgeFile:
        row = KnowledgeFile(
            id=file_id,
            bot_id=bot_id,
            owner_id=owner_id,
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            processing_status=processing_status,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def list_knowledge_files_for_bot(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeFile]:
        stmt = (
            select(KnowledgeFile)
            .where(
                KnowledgeFile.bot_id == bot_id,
                KnowledgeFile.owner_id == owner_id,
            )
            .order_by(KnowledgeFile.uploaded_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 500))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_knowledge_files_for_bot(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count(KnowledgeFile.id)).where(
            KnowledgeFile.bot_id == bot_id,
            KnowledgeFile.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_ready_knowledge_files_for_bot(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> int:
        """Files in ``ready`` state (processed chunks available for retrieval)."""
        stmt = select(func.count(KnowledgeFile.id)).where(
            KnowledgeFile.bot_id == bot_id,
            KnowledgeFile.owner_id == owner_id,
            KnowledgeFile.processing_status == "ready",
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_total_storage_bytes_for_owner(self, owner_id: uuid.UUID) -> int:
        """Sum of ``file_size_bytes`` across all knowledge files owned by ``owner_id``."""
        stmt = select(func.coalesce(func.sum(KnowledgeFile.file_size_bytes), 0)).where(
            KnowledgeFile.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, file_id: uuid.UUID) -> KnowledgeFile | None:
        return await self._session.get(KnowledgeFile, file_id)

    async def try_claim_for_processing(self, file_id: uuid.UUID) -> KnowledgeFile | None:
        """
        Move ``uploaded`` or ``failed`` -> ``processing`` if eligible.

        Returns the row after claim, or ``None`` if no row was updated (wrong state or missing).
        Safe for concurrent workers: at most one claim succeeds.
        """
        stmt = (
            update(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.processing_status.in_(("uploaded", "failed")),
            )
            .values(
                processing_status="processing",
                processing_error=None,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            return None
        row = await self._session.get(KnowledgeFile, file_id)
        return row

    async def mark_processing_failed(
        self,
        file_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        message: str | None,
    ) -> None:
        await self._session.execute(
            update(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.owner_id == owner_id,
                KnowledgeFile.bot_id == bot_id,
            )
            .values(
                processing_status="failed",
                processing_error=message,
                page_count=None,
            ),
        )

    async def mark_processing_ready(
        self,
        file_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        page_count: int | None,
    ) -> None:
        await self._session.execute(
            update(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.owner_id == owner_id,
                KnowledgeFile.bot_id == bot_id,
            )
            .values(
                processing_status="ready",
                processing_error=None,
                page_count=page_count,
                ingestion_failure_count=0,
            ),
        )

    async def increment_ingestion_failure_count(self, file_id: uuid.UUID) -> int | None:
        """Increment after a failed processing run; returns new count or None if row missing."""
        stmt = (
            update(KnowledgeFile)
            .where(KnowledgeFile.id == file_id)
            .values(ingestion_failure_count=KnowledgeFile.ingestion_failure_count + 1)
            .returning(KnowledgeFile.ingestion_failure_count)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_processing_dead_letter(self, file_id: uuid.UUID) -> None:
        await self._session.execute(
            update(KnowledgeFile)
            .where(
                KnowledgeFile.id == file_id,
                KnowledgeFile.processing_status == "failed",
            )
            .values(processing_status="dead_letter"),
        )

    async def get_by_id_for_bot_owner(
        self,
        file_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> KnowledgeFile | None:
        stmt = select(KnowledgeFile).where(
            KnowledgeFile.id == file_id,
            KnowledgeFile.owner_id == owner_id,
            KnowledgeFile.bot_id == bot_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
