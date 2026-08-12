"""
Cost-aware selection of retrieved chunks for LLM prompts.

Takes an **ordered** retrieval list (best first), walks it once, and keeps a prefix that fits
explicit ``max_chunks`` and ``max_total_tokens_estimated`` caps. No string concatenation here:
callers assemble prompts from :class:`SelectedKnowledgeContextItem` rows.

**Future hooks:** swap :func:`estimate_tokens_for_chunk` for model-specific tokenizers; inject
plan/bot overrides into :class:`KnowledgeContextBudget` at the service layer without changing
this module’s core loop.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True, slots=True)
class KnowledgeContextBudget:
    """
    Explicit caps (no implicit defaults inside the selector).

    Construct from :class:`~app.core.config.Settings` plus optional request/bot overrides upstream.
    """

    max_chunks: int
    max_total_tokens_estimated: int
    chars_per_token_estimate: float

    def __post_init__(self) -> None:
        if self.max_chunks < 1:
            raise ValueError("max_chunks must be at least 1")
        if self.max_total_tokens_estimated < 1:
            raise ValueError("max_total_tokens_estimated must be at least 1")
        if self.chars_per_token_estimate <= 0:
            raise ValueError("chars_per_token_estimate must be positive")


@runtime_checkable
class RetrievalHitForContext(Protocol):
    """Structural type for retrieval rows entering context selection."""

    chunk_id: uuid.UUID
    knowledge_file_id: uuid.UUID
    chunk_index: int
    content: str
    rank: float
    page_number: int | None
    original_filename: str
    token_count: int | None


@dataclass(frozen=True, slots=True)
class SelectedKnowledgeContextItem:
    """One chunk approved for the prompt (relevance order preserved)."""

    chunk_id: uuid.UUID
    content: str
    estimated_tokens: int
    rank: float
    page_number: int | None
    original_filename: str
    knowledge_file_id: uuid.UUID
    chunk_index: int


@dataclass(frozen=True, slots=True)
class KnowledgeContextSelectionResult:
    items: tuple[SelectedKnowledgeContextItem, ...]
    total_estimated_tokens: int
    chunks_retrieved: int
    chunks_selected: int
    budget: KnowledgeContextBudget


def estimate_tokens_for_chunk(
    content: str,
    *,
    stored_token_count: int | None,
    chars_per_token_estimate: float,
) -> int:
    """
    Token estimate for budgeting (not billing).

    Prefer persisted ``token_count`` from ingestion when present; otherwise ``chars / estimate``.
    """
    if stored_token_count is not None and stored_token_count > 0:
        return int(stored_token_count)
    text = (content or "").strip()
    if not text:
        return 0
    return max(1, int(math.ceil(len(text) / chars_per_token_estimate)))


def select_knowledge_context(
    hits: Sequence[RetrievalHitForContext],
    *,
    budget: KnowledgeContextBudget,
) -> KnowledgeContextSelectionResult:
    """
    Select a prefix of ``hits`` in order until chunk count or estimated-token sum exceeds budget.
    """
    selected: list[SelectedKnowledgeContextItem] = []
    total = 0

    for h in hits:
        if len(selected) >= budget.max_chunks:
            break
        est = estimate_tokens_for_chunk(
            h.content,
            stored_token_count=h.token_count,
            chars_per_token_estimate=budget.chars_per_token_estimate,
        )
        if est <= 0:
            continue
        if total + est > budget.max_total_tokens_estimated:
            break
        selected.append(
            SelectedKnowledgeContextItem(
                chunk_id=h.chunk_id,
                content=h.content,
                estimated_tokens=est,
                rank=h.rank,
                page_number=h.page_number,
                original_filename=h.original_filename,
                knowledge_file_id=h.knowledge_file_id,
                chunk_index=h.chunk_index,
            )
        )
        total += est

    return KnowledgeContextSelectionResult(
        items=tuple(selected),
        total_estimated_tokens=total,
        chunks_retrieved=len(hits),
        chunks_selected=len(selected),
        budget=budget,
    )
