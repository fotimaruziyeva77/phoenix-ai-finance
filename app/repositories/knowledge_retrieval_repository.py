"""
PostgreSQL full-text search over ``knowledge_chunks`` (bot + owner scoped).

Uses the ``simple`` text search config so tokenization is predictable across languages
without aggressive stemming. Scoring is ``ts_rank`` for explainable ordering.

When FTS returns zero results, a trigram similarity fallback (``pg_trgm``) provides
fuzzy matching so multi-word queries that don't share exact lexemes still surface
relevant content.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile

_FTS_CONFIG = "simple"


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalRow:
    chunk_id: uuid.UUID
    knowledge_file_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    content: str
    token_count: int | None
    original_filename: str
    rank: float


class KnowledgeRetrievalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_full_text(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[KnowledgeRetrievalRow]:
        """
        Return chunks whose content matches the query, ordered by relevance.

        Rows are restricted to ``owner_id`` and ``bot_id`` on ``knowledge_chunks`` and
        joined files in ``ready`` state only.

        Strategy (three-tier):
        1. ``websearch_to_tsquery`` -- strict, supports operators.
        2. ``plainto_tsquery`` -- lenient, treats all words as plain tokens.
        3. ``pg_trgm`` similarity -- fuzzy character-level matching (trigram).

        Each tier is tried only when the previous one returns zero results. This way exact
        FTS matches always win, but multi-word queries whose word forms don't exist in the
        corpus can still surface content via trigram similarity.
        """
        # Tier 1: strict websearch_to_tsquery
        rows = await self._run_fts_query(
            owner_id=owner_id,
            bot_id=bot_id,
            tsq=func.websearch_to_tsquery(_FTS_CONFIG, query),
            limit=limit,
        )
        if rows:
            return rows

        # Tier 2: lenient plainto_tsquery (no special operators, safer for arbitrary input)
        rows = await self._run_fts_query(
            owner_id=owner_id,
            bot_id=bot_id,
            tsq=func.plainto_tsquery(_FTS_CONFIG, query),
            limit=limit,
        )
        if rows:
            return rows

        # Tier 3: trigram similarity fallback (pg_trgm)
        return await self._run_trigram_query(
            owner_id=owner_id,
            bot_id=bot_id,
            query=query,
            limit=limit,
        )

    async def _run_fts_query(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        tsq: object,
        limit: int,
    ) -> list[KnowledgeRetrievalRow]:
        """Execute a single FTS query with the given ``tsquery`` expression."""
        tsv = func.to_tsvector(_FTS_CONFIG, KnowledgeChunk.content)
        rank = func.ts_rank(tsv, tsq)

        stmt = (
            select(
                KnowledgeChunk.id,
                KnowledgeChunk.knowledge_file_id,
                KnowledgeChunk.chunk_index,
                KnowledgeChunk.page_number,
                KnowledgeChunk.content,
                KnowledgeChunk.token_count,
                KnowledgeFile.original_filename,
                rank.label("rank"),
            )
            .join(KnowledgeFile, KnowledgeFile.id == KnowledgeChunk.knowledge_file_id)
            .where(
                KnowledgeChunk.owner_id == owner_id,
                KnowledgeChunk.bot_id == bot_id,
                KnowledgeFile.owner_id == owner_id,
                KnowledgeFile.bot_id == bot_id,
                KnowledgeFile.processing_status == "ready",
                tsv.op("@@")(tsq),
            )
            .order_by(rank.desc(), KnowledgeChunk.knowledge_file_id, KnowledgeChunk.chunk_index)
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            KnowledgeRetrievalRow(
                chunk_id=r.id,
                knowledge_file_id=r.knowledge_file_id,
                chunk_index=r.chunk_index,
                page_number=r.page_number,
                content=r.content,
                token_count=r.token_count,
                original_filename=r.original_filename,
                rank=float(r.rank or 0.0),
            )
            for r in rows
        ]

    async def _run_trigram_query(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[KnowledgeRetrievalRow]:
        """Fuzzy trigram similarity search using the ``pg_trgm`` ``%`` operator.

        Uses the default similarity threshold (0.3). Results are ordered by descending
        similarity score so the most textually similar chunks appear first.
        """
        sim_score = func.similarity(KnowledgeChunk.content, query)

        stmt = (
            select(
                KnowledgeChunk.id,
                KnowledgeChunk.knowledge_file_id,
                KnowledgeChunk.chunk_index,
                KnowledgeChunk.page_number,
                KnowledgeChunk.content,
                KnowledgeChunk.token_count,
                KnowledgeFile.original_filename,
                sim_score.label("rank"),
            )
            .join(KnowledgeFile, KnowledgeFile.id == KnowledgeChunk.knowledge_file_id)
            .where(
                KnowledgeChunk.owner_id == owner_id,
                KnowledgeChunk.bot_id == bot_id,
                KnowledgeFile.owner_id == owner_id,
                KnowledgeFile.bot_id == bot_id,
                KnowledgeFile.processing_status == "ready",
                KnowledgeChunk.content.op("%")(query),
            )
            .order_by(sim_score.desc(), KnowledgeChunk.knowledge_file_id, KnowledgeChunk.chunk_index)
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            KnowledgeRetrievalRow(
                chunk_id=r.id,
                knowledge_file_id=r.knowledge_file_id,
                chunk_index=r.chunk_index,
                page_number=r.page_number,
                content=r.content,
                token_count=r.token_count,
                original_filename=r.original_filename,
                rank=float(r.rank or 0.0),
            )
            for r in rows
        ]
