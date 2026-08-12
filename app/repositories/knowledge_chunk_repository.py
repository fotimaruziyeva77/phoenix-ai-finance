from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from app.services.knowledge_text_chunking import ChunkSpec


class KnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete_chunks_for_file(
        self,
        knowledge_file_id: uuid.UUID,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
    ) -> None:
        """Delete chunks only when file id matches tenant scope (defense in depth)."""
        await self._session.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.knowledge_file_id == knowledge_file_id,
                KnowledgeChunk.owner_id == owner_id,
                KnowledgeChunk.bot_id == bot_id,
            ),
        )

    async def insert_chunks_for_file(
        self,
        file_row: KnowledgeFile,
        chunks: Sequence[ChunkSpec],
    ) -> None:
        """Append chunks for a file. Caller should delete existing chunks first for idempotent replace."""
        rows: list[KnowledgeChunk] = []
        for idx, spec in enumerate(chunks):
            rows.append(
                KnowledgeChunk(
                    knowledge_file_id=file_row.id,
                    bot_id=file_row.bot_id,
                    owner_id=file_row.owner_id,
                    chunk_index=idx,
                    page_number=spec.page_number,
                    content=spec.content,
                    token_count=spec.token_count,
                )
            )
        self._session.add_all(rows)
        await self._session.flush()
