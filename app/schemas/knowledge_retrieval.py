"""API / service DTOs for knowledge chunk retrieval."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class KnowledgeRetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="If omitted, server default applies (capped by max limit).",
    )
    max_context_chunks: int | None = Field(
        default=None,
        ge=1,
        le=512,
        description="Max chunks included in `context` after retrieval (capped by server ceiling).",
    )
    max_context_estimated_tokens: int | None = Field(
        default=None,
        ge=1,
        le=4_000_000,
        description="Estimated-token budget for `context` (capped by server ceiling).",
    )


class KnowledgeChunkHit(BaseModel):
    chunk_id: uuid.UUID
    knowledge_file_id: uuid.UUID
    chunk_index: int
    content: str
    rank: float = Field(description="PostgreSQL ts_rank (higher is more relevant).")
    page_number: int | None = None
    original_filename: str = Field(description="Source PDF filename for citations.")
    token_count: int | None = Field(
        default=None,
        description="Stored estimate from ingestion; context selection uses this when set.",
    )


class KnowledgeContextItem(BaseModel):
    """Budgeted slice for prompt assembly (single copy of body text for LLM)."""

    chunk_id: uuid.UUID
    knowledge_file_id: uuid.UUID
    chunk_index: int
    content: str
    estimated_tokens: int
    rank: float
    page_number: int | None = None
    original_filename: str


class KnowledgeContextSelectionMeta(BaseModel):
    """Echoes the caps that were applied (auditable; no hidden limits)."""

    chunks_retrieved: int
    chunks_in_context: int
    total_estimated_tokens: int
    max_chunks_applied: int
    max_total_tokens_estimated_applied: int


class KnowledgeRetrievalResponse(BaseModel):
    query: str
    bot_id: uuid.UUID
    hits: list[KnowledgeChunkHit]
    context: list[KnowledgeContextItem] = Field(
        default_factory=list,
        description="Cost-bounded subset of hits in relevance order; use this for LLM prompts.",
    )
    context_meta: KnowledgeContextSelectionMeta | None = None
