"""Unit tests for :class:`~app.services.knowledge_retrieval_service.KnowledgeRetrievalService`."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import Settings
from app.repositories.knowledge_retrieval_repository import KnowledgeRetrievalRow
from app.services.bot_exceptions import BotNotFoundError
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService


def _user(uid: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uid or uuid.uuid4()
    return u


@pytest.mark.asyncio
async def test_retrieve_empty_query_returns_no_hits() -> None:
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    bot_id = uuid.uuid4()
    out = await svc.retrieve_for_bot(_user(), bot_id, query="   ", limit=10)
    assert out.hits == []
    assert out.bot_id == bot_id
    assert out.query == ""
    assert out.context == []
    assert out.context_meta is not None
    assert out.context_meta.chunks_in_context == 0


@pytest.mark.asyncio
async def test_empty_query_short_circuits_no_bot_or_search() -> None:
    """Safe handling: whitespace-only query must not hit DB or bot ownership check."""
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    svc._bots.exists_for_owner = AsyncMock()  # type: ignore[method-assign]
    svc._retrieval.search_full_text = AsyncMock()  # type: ignore[method-assign]
    await svc.retrieve_for_bot(_user(), uuid.uuid4(), query="\t\n", limit=5)
    svc._bots.exists_for_owner.assert_not_called()
    svc._retrieval.search_full_text.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_raises_when_bot_not_owned() -> None:
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    svc._bots.exists_for_owner = AsyncMock(return_value=False)  # type: ignore[method-assign]
    with pytest.raises(BotNotFoundError):
        await svc.retrieve_for_bot(_user(), uuid.uuid4(), query="hello", limit=5)


@pytest.mark.asyncio
async def test_retrieve_maps_repository_rows_to_hits() -> None:
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    svc._bots.exists_for_owner = AsyncMock(return_value=True)  # type: ignore[method-assign]

    cid = uuid.uuid4()
    fid = uuid.uuid4()
    svc._retrieval.search_full_text = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            KnowledgeRetrievalRow(
                chunk_id=cid,
                knowledge_file_id=fid,
                chunk_index=0,
                page_number=2,
                content="snippet about refunds",
                token_count=10,
                original_filename="policy.pdf",
                rank=0.42,
            ),
        ],
    )

    user = _user()
    bot_id = uuid.uuid4()
    out = await svc.retrieve_for_bot(
        user,
        bot_id,
        query="refunds",
        limit=5,
        max_context_chunks=10,
        max_context_estimated_tokens=10_000,
    )
    assert len(out.hits) == 1
    h = out.hits[0]
    assert h.chunk_id == cid
    assert h.knowledge_file_id == fid
    assert h.chunk_index == 0
    assert h.page_number == 2
    assert h.content == "snippet about refunds"
    assert h.rank == 0.42
    assert h.original_filename == "policy.pdf"
    assert h.token_count == 10
    assert len(out.context) == 1
    assert out.context[0].chunk_id == cid
    assert out.context[0].estimated_tokens == 10
    assert out.context_meta is not None
    assert out.context_meta.chunks_in_context == 1
    assert out.context_meta.total_estimated_tokens == 10
    svc._retrieval.search_full_text.assert_awaited_once()
    call_kw = svc._retrieval.search_full_text.await_args.kwargs
    assert call_kw["owner_id"] == user.id
    assert call_kw["bot_id"] == bot_id
    assert call_kw["query"] == "refunds"


@pytest.mark.asyncio
async def test_empty_search_results_safe_context_and_meta() -> None:
    """4. No FTS hits: empty context, no error, meta reflects zero selection."""
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    svc._bots.exists_for_owner = AsyncMock(return_value=True)  # type: ignore[method-assign]
    svc._retrieval.search_full_text = AsyncMock(return_value=[])  # type: ignore[method-assign]

    out = await svc.retrieve_for_bot(_user(), uuid.uuid4(), query="something", limit=10)
    assert out.hits == []
    assert out.context == []
    assert out.context_meta is not None
    assert out.context_meta.chunks_retrieved == 0
    assert out.context_meta.chunks_in_context == 0
    assert out.context_meta.total_estimated_tokens == 0


@pytest.mark.asyncio
async def test_context_budget_truncates_before_hit_cap() -> None:
    session = AsyncMock()
    settings = Settings(environment="local", jwt_secret_key="x" * 32)
    svc = KnowledgeRetrievalService(session, settings)
    svc._bots.exists_for_owner = AsyncMock(return_value=True)  # type: ignore[method-assign]

    rows = [
        KnowledgeRetrievalRow(
            chunk_id=uuid.uuid4(),
            knowledge_file_id=uuid.uuid4(),
            chunk_index=i,
            page_number=1,
            content="word " * 20,
            token_count=100,
            original_filename="f.pdf",
            rank=1.0 - i * 0.1,
        )
        for i in range(4)
    ]
    svc._retrieval.search_full_text = AsyncMock(return_value=rows)  # type: ignore[method-assign]

    out = await svc.retrieve_for_bot(
        _user(),
        uuid.uuid4(),
        query="word",
        limit=10,
        max_context_chunks=10,
        max_context_estimated_tokens=250,
    )
    assert len(out.hits) == 4
    assert len(out.context) == 2
    assert out.context_meta is not None
    assert out.context_meta.total_estimated_tokens == 200
    assert out.context_meta.chunks_in_context == 2


def test_retrieval_response_schema_supports_prompt_citations() -> None:
    """Fields a prompt builder typically needs: text, source file, page, stable id, relevance."""
    from app.schemas.knowledge_retrieval import (
        KnowledgeChunkHit,
        KnowledgeContextItem,
        KnowledgeContextSelectionMeta,
        KnowledgeRetrievalResponse,
    )

    bid = uuid.uuid4()
    cid = uuid.uuid4()
    fid = uuid.uuid4()
    hit = KnowledgeChunkHit(
        chunk_id=cid,
        knowledge_file_id=fid,
        chunk_index=2,
        content="Body text from PDF.",
        rank=0.15,
        page_number=7,
        original_filename="handbook.pdf",
        token_count=5,
    )
    ctx = KnowledgeContextItem(
        chunk_id=cid,
        knowledge_file_id=fid,
        chunk_index=2,
        content="Body text from PDF.",
        estimated_tokens=5,
        rank=0.15,
        page_number=7,
        original_filename="handbook.pdf",
    )
    meta = KnowledgeContextSelectionMeta(
        chunks_retrieved=1,
        chunks_in_context=1,
        total_estimated_tokens=5,
        max_chunks_applied=5,
        max_total_tokens_estimated_applied=4000,
    )
    body = KnowledgeRetrievalResponse(
        query="warranty",
        bot_id=bid,
        hits=[hit],
        context=[ctx],
        context_meta=meta,
    ).model_dump(mode="json")
    assert body["query"] == "warranty"
    assert body["bot_id"] == str(bid)
    assert len(body["hits"]) == 1
    h = body["hits"][0]
    assert set(h.keys()) >= {
        "chunk_id",
        "knowledge_file_id",
        "chunk_index",
        "content",
        "rank",
        "page_number",
        "original_filename",
        "token_count",
    }
    assert h["content"] == "Body text from PDF."
    assert h["page_number"] == 7
    assert h["original_filename"] == "handbook.pdf"
    assert body["context"][0]["estimated_tokens"] == 5
    assert body["context_meta"]["chunks_in_context"] == 1


@pytest.mark.asyncio
async def test_effective_limit_clamps_to_settings_max() -> None:
    session = AsyncMock()
    settings = Settings(
        environment="local",
        jwt_secret_key="x" * 32,
        knowledge_retrieval_default_limit=5,
        knowledge_retrieval_max_limit=7,
    )
    svc = KnowledgeRetrievalService(session, settings)
    assert svc._effective_limit(None) == 5
    assert svc._effective_limit(100) == 7
    assert svc._effective_limit(3) == 3
