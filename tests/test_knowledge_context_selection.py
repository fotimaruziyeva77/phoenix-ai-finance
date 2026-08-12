"""Unit tests for :mod:`app.services.knowledge_context_selection`.

Covers relevance order, token and chunk caps, empty input, and prompt-builder-friendly output.
"""

from __future__ import annotations

import uuid

import pytest
from app.schemas.knowledge_retrieval import KnowledgeContextItem
from app.services.knowledge_context_selection import (
    KnowledgeContextBudget,
    estimate_tokens_for_chunk,
    select_knowledge_context,
)


class _Hit:
    __slots__ = (
        "chunk_id",
        "knowledge_file_id",
        "chunk_index",
        "content",
        "rank",
        "page_number",
        "original_filename",
        "token_count",
    )

    def __init__(
        self,
        *,
        content: str,
        token_count: int | None,
        rank: float = 1.0,
        chunk_index: int = 0,
        page_number: int | None = 1,
        filename: str = "x.pdf",
    ) -> None:
        self.chunk_id = uuid.uuid4()
        self.knowledge_file_id = uuid.uuid4()
        self.chunk_index = chunk_index
        self.content = content
        self.rank = rank
        self.page_number = page_number
        self.original_filename = filename
        self.token_count = token_count


def test_estimate_tokens_uses_stored_count_when_positive() -> None:
    assert estimate_tokens_for_chunk("hello", stored_token_count=99, chars_per_token_estimate=4.0) == 99


def test_estimate_tokens_falls_back_to_chars() -> None:
    assert estimate_tokens_for_chunk("abcd", stored_token_count=None, chars_per_token_estimate=2.0) == 2


def test_select_respects_max_chunks_in_order() -> None:
    hits = [
        _Hit(content="a", token_count=1, rank=1.0),
        _Hit(content="b", token_count=1, rank=0.5),
        _Hit(content="c", token_count=1, rank=0.25),
    ]
    budget = KnowledgeContextBudget(max_chunks=2, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 2
    assert [x.content for x in r.items] == ["a", "b"]
    assert r.total_estimated_tokens == 2


def test_select_stops_at_token_budget() -> None:
    hits = [
        _Hit(content="a", token_count=45, rank=1.0),
        _Hit(content="b", token_count=45, rank=0.9),
        _Hit(content="c", token_count=20, rank=0.8),
    ]
    budget = KnowledgeContextBudget(max_chunks=10, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 2
    assert r.total_estimated_tokens == 90
    assert r.items[0].content == "a" and r.items[1].content == "b"


def test_select_skips_zero_token_empty_content() -> None:
    hits = [_Hit(content="   ", token_count=None, rank=1.0), _Hit(content="ok", token_count=2, rank=0.5)]
    budget = KnowledgeContextBudget(max_chunks=5, max_total_tokens_estimated=50, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert len(r.items) == 1
    assert r.items[0].content == "ok"


def test_budget_validation() -> None:
    with pytest.raises(ValueError, match="max_chunks"):
        KnowledgeContextBudget(max_chunks=0, max_total_tokens_estimated=10, chars_per_token_estimate=4.0)
    with pytest.raises(ValueError, match="max_total_tokens_estimated"):
        KnowledgeContextBudget(max_chunks=1, max_total_tokens_estimated=0, chars_per_token_estimate=4.0)
    with pytest.raises(ValueError, match="chars_per_token_estimate"):
        KnowledgeContextBudget(max_chunks=1, max_total_tokens_estimated=10, chars_per_token_estimate=0.0)


# --- 1. Top relevant first (input list order = retrieval order; never re-sorted) ---


def test_selection_preserves_retrieval_order_not_lexicographic() -> None:
    """Later high-signal chunk does not jump ahead of earlier lower-rank hit."""
    hits = [
        _Hit(content="zebra first", token_count=1, rank=0.9, chunk_index=0),
        _Hit(content="alpha second", token_count=1, rank=0.1, chunk_index=1),
        _Hit(content="beta third", token_count=1, rank=0.99, chunk_index=2),
    ]
    budget = KnowledgeContextBudget(max_chunks=3, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert [x.content for x in r.items] == ["zebra first", "alpha second", "beta third"]
    assert [x.rank for x in r.items] == [0.9, 0.1, 0.99]


def test_first_highest_rank_chunk_is_first_in_context() -> None:
    hits = [
        _Hit(content="best", token_count=5, rank=0.95, chunk_index=0),
        _Hit(content="worse", token_count=5, rank=0.12, chunk_index=1),
    ]
    budget = KnowledgeContextBudget(max_chunks=1, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert len(r.items) == 1
    assert r.items[0].content == "best"
    assert r.items[0].rank == 0.95


# --- 2. Token budget ---


def test_token_budget_allows_exact_fill() -> None:
    """total + est == max_total_tokens_estimated is allowed (no off-by-one)."""
    hits = [
        _Hit(content="a", token_count=50, rank=1.0),
        _Hit(content="b", token_count=50, rank=0.9),
    ]
    budget = KnowledgeContextBudget(max_chunks=10, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 2
    assert r.total_estimated_tokens == 100


def test_single_chunk_exceeding_total_budget_selects_nothing() -> None:
    hits = [_Hit(content="only", token_count=500, rank=1.0)]
    budget = KnowledgeContextBudget(max_chunks=5, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.items == ()
    assert r.total_estimated_tokens == 0
    assert r.chunks_selected == 0


def test_stored_token_count_zero_falls_back_to_char_estimate() -> None:
    assert estimate_tokens_for_chunk("abcd", stored_token_count=0, chars_per_token_estimate=2.0) == 2


# --- 3. Chunk cap vs many small chunks (no overflow past max_chunks) ---


def test_max_chunks_caps_even_with_huge_token_budget() -> None:
    hits = [_Hit(content=f"c{i}", token_count=1, rank=1.0 - i * 0.01, chunk_index=i) for i in range(20)]
    budget = KnowledgeContextBudget(
        max_chunks=3,
        max_total_tokens_estimated=1_000_000,
        chars_per_token_estimate=4.0,
    )
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 3
    assert r.total_estimated_tokens == 3
    assert [x.chunk_index for x in r.items] == [0, 1, 2]


# --- 4. Empty retrieval ---


def test_empty_hits_returns_empty_selection() -> None:
    budget = KnowledgeContextBudget(max_chunks=5, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context([], budget=budget)
    assert r.items == ()
    assert r.chunks_retrieved == 0
    assert r.chunks_selected == 0
    assert r.total_estimated_tokens == 0
    assert r.budget == budget


def test_all_hits_skip_due_to_empty_yields_empty_context() -> None:
    hits = [_Hit(content="  ", token_count=None, rank=1.0), _Hit(content="\n", token_count=None, rank=0.5)]
    budget = KnowledgeContextBudget(max_chunks=5, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.items == ()
    assert r.total_estimated_tokens == 0


# --- 5. Prompt-builder-ready shape ---


def test_selected_items_contain_citation_and_body_fields() -> None:
    h = _Hit(
        content="Policy paragraph for the model.",
        token_count=12,
        rank=0.33,
        chunk_index=4,
        page_number=7,
        filename="Terms_v2.pdf",
    )
    budget = KnowledgeContextBudget(max_chunks=5, max_total_tokens_estimated=500, chars_per_token_estimate=4.0)
    r = select_knowledge_context([h], budget=budget)
    item = r.items[0]
    block = (
        f"[{item.original_filename} p.{item.page_number} chunk={item.chunk_index} "
        f"id={item.chunk_id}]\n{item.content}"
    )
    assert "Terms_v2.pdf" in block
    assert "Policy paragraph" in block
    assert item.estimated_tokens == 12

    pydantic = KnowledgeContextItem(
        chunk_id=item.chunk_id,
        knowledge_file_id=item.knowledge_file_id,
        chunk_index=item.chunk_index,
        content=item.content,
        estimated_tokens=item.estimated_tokens,
        rank=item.rank,
        page_number=item.page_number,
        original_filename=item.original_filename,
    )
    dumped = pydantic.model_dump(mode="json")
    assert set(dumped.keys()) >= {
        "chunk_id",
        "knowledge_file_id",
        "chunk_index",
        "content",
        "estimated_tokens",
        "rank",
        "page_number",
        "original_filename",
    }


# --- Budget edge cases ---


def test_first_chunk_fits_second_would_exceed_stops_without_second() -> None:
    hits = [
        _Hit(content="a", token_count=60, rank=1.0),
        _Hit(content="b", token_count=50, rank=0.9),
    ]
    budget = KnowledgeContextBudget(max_chunks=10, max_total_tokens_estimated=100, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 1
    assert r.total_estimated_tokens == 60


def test_max_chunks_one_with_large_token_budget_only_first() -> None:
    hits = [
        _Hit(content="a", token_count=5, rank=1.0),
        _Hit(content="b", token_count=5, rank=0.5),
    ]
    budget = KnowledgeContextBudget(max_chunks=1, max_total_tokens_estimated=10_000, chars_per_token_estimate=4.0)
    r = select_knowledge_context(hits, budget=budget)
    assert r.chunks_selected == 1
    assert r.items[0].content == "a"
