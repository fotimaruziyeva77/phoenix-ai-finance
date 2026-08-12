"""
Owner-scoped knowledge retrieval for a single bot (MVP full-text search).

Design (MVP)
------------
We use **PostgreSQL full-text search** with the ``simple`` dictionary and
``websearch_to_tsquery`` so user phrases behave intuitively, matches are **SQL-explainable**
(``@@`` + ``ts_rank``), and we can add a **GIN** index on ``to_tsvector(content)`` without
application state. This avoids shipping a vector DB while staying more principled than ad-hoc
``ILIKE`` token splitting.

**No cross-bot leakage:** queries always filter ``knowledge_chunks.bot_id``,
``knowledge_chunks.owner_id``, and the same on the joined ``knowledge_files`` row. Callers must
pass an ``owner_id`` that has already been authenticated; we also verify the bot belongs to that
owner before searching.

**Testability:** ranking is entirely in SQL; the service is a thin policy layer (limits, bot check).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.repositories.knowledge_retrieval_repository import KnowledgeRetrievalRepository
from app.schemas.knowledge_retrieval import (
    KnowledgeChunkHit,
    KnowledgeContextItem,
    KnowledgeContextSelectionMeta,
    KnowledgeRetrievalResponse,
)
from app.services.bot_exceptions import BotNotFoundError
from app.services.knowledge_context_selection import (
    KnowledgeContextBudget,
    select_knowledge_context,
)


class KnowledgeRetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self._session = session
        self._settings = settings
        self._bots = BotRepository(session)
        self._retrieval = KnowledgeRetrievalRepository(session)

    def _effective_limit(self, requested: int | None) -> int:
        cap = self._settings.knowledge_retrieval_max_limit
        default = min(self._settings.knowledge_retrieval_default_limit, cap)
        if requested is None:
            return default
        return min(max(requested, 1), cap)

    def _resolve_context_budget(
        self,
        max_context_chunks: int | None,
        max_context_estimated_tokens: int | None,
    ) -> KnowledgeContextBudget:
        s = self._settings
        chunks = (
            max_context_chunks
            if max_context_chunks is not None
            else s.knowledge_context_default_max_chunks
        )
        tokens = (
            max_context_estimated_tokens
            if max_context_estimated_tokens is not None
            else s.knowledge_context_default_max_estimated_tokens
        )
        chunks = min(max(chunks, 1), s.knowledge_context_max_chunks_ceiling)
        tokens = min(max(tokens, 1), s.knowledge_context_max_estimated_tokens_ceiling)
        return KnowledgeContextBudget(
            max_chunks=chunks,
            max_total_tokens_estimated=tokens,
            chars_per_token_estimate=s.ai_token_chars_per_token_estimate,
        )

    def _empty_retrieval_response(
        self,
        *,
        bot_id: uuid.UUID,
        query: str,
        max_context_chunks: int | None,
        max_context_estimated_tokens: int | None,
    ) -> KnowledgeRetrievalResponse:
        budget = self._resolve_context_budget(max_context_chunks, max_context_estimated_tokens)
        meta = KnowledgeContextSelectionMeta(
            chunks_retrieved=0,
            chunks_in_context=0,
            total_estimated_tokens=0,
            max_chunks_applied=budget.max_chunks,
            max_total_tokens_estimated_applied=budget.max_total_tokens_estimated,
        )
        return KnowledgeRetrievalResponse(
            query=query,
            bot_id=bot_id,
            hits=[],
            context=[],
            context_meta=meta,
        )

    async def retrieve_for_bot(
        self,
        current_user: User,
        bot_id: uuid.UUID,
        *,
        query: str,
        limit: int | None = None,
        max_context_chunks: int | None = None,
        max_context_estimated_tokens: int | None = None,
    ) -> KnowledgeRetrievalResponse:
        q = (query or "").strip()
        if not q:
            return self._empty_retrieval_response(
                bot_id=bot_id,
                query="",
                max_context_chunks=max_context_chunks,
                max_context_estimated_tokens=max_context_estimated_tokens,
            )

        if not await self._bots.exists_for_owner(owner_id=current_user.id, bot_id=bot_id):
            raise BotNotFoundError()

        eff_limit = self._effective_limit(limit)
        rows = await self._retrieval.search_full_text(
            owner_id=current_user.id,
            bot_id=bot_id,
            query=q,
            limit=eff_limit,
        )
        hits = [
            KnowledgeChunkHit(
                chunk_id=r.chunk_id,
                knowledge_file_id=r.knowledge_file_id,
                chunk_index=r.chunk_index,
                content=r.content,
                rank=r.rank,
                page_number=r.page_number,
                original_filename=r.original_filename,
                token_count=r.token_count,
            )
            for r in rows
        ]
        budget = self._resolve_context_budget(max_context_chunks, max_context_estimated_tokens)
        selection = select_knowledge_context(hits, budget=budget)
        context = [
            KnowledgeContextItem(
                chunk_id=c.chunk_id,
                knowledge_file_id=c.knowledge_file_id,
                chunk_index=c.chunk_index,
                content=c.content,
                estimated_tokens=c.estimated_tokens,
                rank=c.rank,
                page_number=c.page_number,
                original_filename=c.original_filename,
            )
            for c in selection.items
        ]
        meta = KnowledgeContextSelectionMeta(
            chunks_retrieved=selection.chunks_retrieved,
            chunks_in_context=selection.chunks_selected,
            total_estimated_tokens=selection.total_estimated_tokens,
            max_chunks_applied=budget.max_chunks,
            max_total_tokens_estimated_applied=budget.max_total_tokens_estimated,
        )
        return KnowledgeRetrievalResponse(query=q, bot_id=bot_id, hits=hits, context=context, context_meta=meta)
