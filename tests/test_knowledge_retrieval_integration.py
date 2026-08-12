"""
PostgreSQL integration tests for knowledge full-text retrieval (bot + owner scoped).

Requires ``TEST_DATABASE_URL`` or host-reachable ``DATABASE_URL``.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from app.models.user import User
from app.repositories.knowledge_retrieval_repository import KnowledgeRetrievalRepository
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService

from tests.db_alembic import run_alembic_upgrade_head
from tests.fixtures.knowledge_retrieval_samples import (
    CHUNK_BILLING_UNRELATED,
    CHUNK_INTL_SHIPPING_DENSE,
    CHUNK_INTL_SHIPPING_SPARSE,
    CHUNK_OTHER_BOT_DECOY,
    CHUNK_REFUND_POLICY,
    CHUNK_RETURNS_DOMESTIC_ONLY,
    QUERY_INTERNATIONAL_SHIPPING,
    QUERY_REFUND,
)
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.knowledge_retrieval,
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason="PostgreSQL URL not configured for integration tests.",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_retrieval() -> None:
    url = _integration_db_url()
    assert url is not None
    run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
async def session_maker(live_db_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    await dispose_engine()
    yield get_session_maker()
    await dispose_engine()
    get_settings.cache_clear()


async def _seed_two_bots_with_chunks(session_maker) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """One owner, two bots; bot_a has chunk with 'voltage', bot_b with 'warranty' only."""
    owner_id = uuid.uuid4()
    bot_a = uuid.uuid4()
    bot_b = uuid.uuid4()
    file_a = uuid.uuid4()
    file_b = uuid.uuid4()

    async with session_maker() as session:
        user = User(
            id=owner_id,
            email=f"ret_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        ba = Bot(id=bot_a, owner_id=owner_id, name="A", niche_id="education", goal_type="faq")
        bb = Bot(id=bot_b, owner_id=owner_id, name="B", niche_id="education", goal_type="faq")
        kfa = KnowledgeFile(
            id=file_a,
            bot_id=bot_a,
            owner_id=owner_id,
            original_filename="manual.pdf",
            storage_key=f"v1/k/{file_a}.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            processing_status="ready",
        )
        kfb = KnowledgeFile(
            id=file_b,
            bot_id=bot_b,
            owner_id=owner_id,
            original_filename="warranty.pdf",
            storage_key=f"v1/k/{file_b}.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            processing_status="ready",
        )
        ca = KnowledgeChunk(
            knowledge_file_id=file_a,
            bot_id=bot_a,
            owner_id=owner_id,
            chunk_index=0,
            page_number=3,
            content="Battery nominal voltage is twelve volts DC.",
            token_count=8,
        )
        cb = KnowledgeChunk(
            knowledge_file_id=file_b,
            bot_id=bot_b,
            owner_id=owner_id,
            chunk_index=0,
            page_number=1,
            content="Standard warranty covers manufacturing defects for one year.",
            token_count=8,
        )
        session.add_all([user, ba, bb, kfa, kfb, ca, cb])
        await session.commit()
    return owner_id, bot_a, bot_b


async def test_repository_full_text_scoped_to_bot(session_maker) -> None:
    owner_id, bot_a, bot_b = await _seed_two_bots_with_chunks(session_maker)

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        hits_a = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_a,
            query="voltage",
            limit=10,
        )
        assert len(hits_a) == 1
        assert "voltage" in hits_a[0].content.lower()
        assert hits_a[0].page_number == 3
        assert hits_a[0].original_filename == "manual.pdf"

        hits_b = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_b,
            query="voltage",
            limit=10,
        )
        assert hits_b == []

        wrong_owner = uuid.uuid4()
        hits_wrong_owner = await repo.search_full_text(
            owner_id=wrong_owner,
            bot_id=bot_a,
            query="voltage",
            limit=10,
        )
        assert hits_wrong_owner == []

        hits_w = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_b,
            query="warranty",
            limit=10,
        )
        assert len(hits_w) == 1
        assert hits_w[0].original_filename == "warranty.pdf"


async def test_repository_ignores_non_ready_files(session_maker) -> None:
    owner_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    file_id = uuid.uuid4()

    async with session_maker() as session:
        user = User(
            id=owner_id,
            email=f"nr_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        bot = Bot(id=bot_id, owner_id=owner_id, name="NR", niche_id="education", goal_type="faq")
        kf = KnowledgeFile(
            id=file_id,
            bot_id=bot_id,
            owner_id=owner_id,
            original_filename="draft.pdf",
            storage_key=f"v1/k/{file_id}.pdf",
            mime_type="application/pdf",
            file_size_bytes=10,
            processing_status="failed",
        )
        chunk = KnowledgeChunk(
            knowledge_file_id=file_id,
            bot_id=bot_id,
            owner_id=owner_id,
            chunk_index=0,
            page_number=0,
            content="zebra uniqueword xyz",
            token_count=3,
        )
        session.add_all([user, bot, kf, chunk])
        await session.commit()

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_id,
            query="uniqueword",
            limit=10,
        )
        assert hits == []


async def test_service_end_to_end_retrieve(session_maker, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner_id, bot_a, _ = await _seed_two_bots_with_chunks(session_maker)
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    settings = get_settings()

    user = User(
        id=owner_id,
        email="u@e.com",
        password_hash="x",
        role=UserRole.customer_admin,
    )

    async with session_maker() as session:
        svc = KnowledgeRetrievalService(session, settings)
        out = await svc.retrieve_for_bot(user, bot_a, query="battery", limit=5)
        assert len(out.hits) >= 1
        assert out.query == "battery"
        assert any("battery" in h.content.lower() for h in out.hits)


async def _seed_realistic_pdf_corpus(session_maker) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """
    One owner, two bots.

    ``bot_main`` has three chunks (international shipping dense/sparse + returns-only).
    ``bot_other`` has a decoy chunk that also mentions international shipping.
    """
    owner_id = uuid.uuid4()
    bot_main = uuid.uuid4()
    bot_other = uuid.uuid4()
    file_main = uuid.uuid4()
    file_other = uuid.uuid4()

    async with session_maker() as session:
        user = User(
            id=owner_id,
            email=f"pdf_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        b_main = Bot(id=bot_main, owner_id=owner_id, name="Main", niche_id="education", goal_type="faq")
        b_other = Bot(id=bot_other, owner_id=owner_id, name="Other", niche_id="education", goal_type="faq")
        k_main = KnowledgeFile(
            id=file_main,
            bot_id=bot_main,
            owner_id=owner_id,
            original_filename="Logistics_Guide.pdf",
            storage_key=f"v1/k/{file_main}.pdf",
            mime_type="application/pdf",
            file_size_bytes=50_000,
            processing_status="ready",
        )
        k_other = KnowledgeFile(
            id=file_other,
            bot_id=bot_other,
            owner_id=owner_id,
            original_filename="Enterprise_SLA.pdf",
            storage_key=f"v1/k/{file_other}.pdf",
            mime_type="application/pdf",
            file_size_bytes=12_000,
            processing_status="ready",
        )
        chunks = [
            KnowledgeChunk(
                knowledge_file_id=file_main,
                bot_id=bot_main,
                owner_id=owner_id,
                chunk_index=0,
                page_number=2,
                content=CHUNK_INTL_SHIPPING_DENSE,
                token_count=40,
            ),
            KnowledgeChunk(
                knowledge_file_id=file_main,
                bot_id=bot_main,
                owner_id=owner_id,
                chunk_index=1,
                page_number=4,
                content=CHUNK_INTL_SHIPPING_SPARSE,
                token_count=40,
            ),
            KnowledgeChunk(
                knowledge_file_id=file_main,
                bot_id=bot_main,
                owner_id=owner_id,
                chunk_index=2,
                page_number=9,
                content=CHUNK_RETURNS_DOMESTIC_ONLY,
                token_count=35,
            ),
            KnowledgeChunk(
                knowledge_file_id=file_other,
                bot_id=bot_other,
                owner_id=owner_id,
                chunk_index=0,
                page_number=1,
                content=CHUNK_OTHER_BOT_DECOY,
                token_count=30,
            ),
        ]
        session.add_all([user, b_main, b_other, k_main, k_other, *chunks])
        await session.commit()
    return owner_id, bot_main, bot_other


async def test_realistic_query_returns_relevant_chunks_ordered_by_rank(session_maker) -> None:
    """1 + 2: relevant chunks returned; denser international-shipping copy ranks above sparse."""
    owner_id, bot_main, _ = await _seed_realistic_pdf_corpus(session_maker)

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_main,
            query=QUERY_INTERNATIONAL_SHIPPING,
            limit=10,
        )
    assert len(hits) == 2
    assert hits[0].rank >= hits[1].rank
    assert CHUNK_INTL_SHIPPING_DENSE[:40] in hits[0].content
    assert hits[0].page_number == 2
    assert hits[0].original_filename == "Logistics_Guide.pdf"
    assert CHUNK_INTL_SHIPPING_SPARSE[:30] in hits[1].content
    for h in hits:
        assert "international" in h.content.lower()


async def test_retrieval_only_target_bot_knowledge_realistic_corpus(session_maker) -> None:
    """3: other bot's PDF (also about international shipping) never appears."""
    owner_id, bot_main, bot_other = await _seed_realistic_pdf_corpus(session_maker)

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        main_hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_main,
            query=QUERY_INTERNATIONAL_SHIPPING,
            limit=10,
        )
        other_hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_other,
            query=QUERY_INTERNATIONAL_SHIPPING,
            limit=10,
        )
    assert len(main_hits) == 2
    assert len(other_hits) == 1
    assert "enterprise" in other_hits[0].content.lower()
    assert all("enterprise" not in h.content.lower() for h in main_hits)


async def test_no_lexeme_match_returns_empty_list(session_maker) -> None:
    """4: no crash; stable empty result."""
    owner_id, bot_main, _ = await _seed_realistic_pdf_corpus(session_maker)

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_main,
            query="xyzzyphantomtokennotindb",
            limit=10,
        )
    assert hits == []


async def test_refund_query_hits_policy_chunk_not_billing(session_maker) -> None:
    """1: user question about refunds surfaces the refund policy paragraph."""
    owner_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    fid = uuid.uuid4()

    async with session_maker() as session:
        user = User(
            id=owner_id,
            email=f"rf_{uuid.uuid4().hex}@example.com",
            password_hash="x",
            role=UserRole.customer_admin,
        )
        bot = Bot(id=bot_id, owner_id=owner_id, name="R", niche_id="education", goal_type="faq")
        kf = KnowledgeFile(
            id=fid,
            bot_id=bot_id,
            owner_id=owner_id,
            original_filename="Customer_Policy.pdf",
            storage_key=f"v1/k/{fid}.pdf",
            mime_type="application/pdf",
            file_size_bytes=20_000,
            processing_status="ready",
        )
        session.add_all(
            [
                user,
                bot,
                kf,
                KnowledgeChunk(
                    knowledge_file_id=fid,
                    bot_id=bot_id,
                    owner_id=owner_id,
                    chunk_index=0,
                    page_number=3,
                    content=CHUNK_REFUND_POLICY,
                    token_count=50,
                ),
                KnowledgeChunk(
                    knowledge_file_id=fid,
                    bot_id=bot_id,
                    owner_id=owner_id,
                    chunk_index=1,
                    page_number=12,
                    content=CHUNK_BILLING_UNRELATED,
                    token_count=40,
                ),
            ],
        )
        await session.commit()

    async with session_maker() as session:
        repo = KnowledgeRetrievalRepository(session)
        hits = await repo.search_full_text(
            owner_id=owner_id,
            bot_id=bot_id,
            query=QUERY_REFUND,
            limit=5,
        )
    assert len(hits) == 1
    assert "refund processing" in hits[0].content.lower()
    assert hits[0].page_number == 3
    assert hits[0].original_filename == "Customer_Policy.pdf"


async def test_service_response_json_ready_for_prompt_builder(
    session_maker,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5: structured, JSON-serializable payload for downstream RAG prompt assembly."""
    import json

    owner_id, bot_main, _ = await _seed_realistic_pdf_corpus(session_maker)
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    get_settings.cache_clear()
    settings = get_settings()
    user = User(id=owner_id, email="x@y.com", password_hash="x", role=UserRole.customer_admin)

    async with session_maker() as session:
        svc = KnowledgeRetrievalService(session, settings)
        out = await svc.retrieve_for_bot(
            user,
            bot_main,
            query=QUERY_INTERNATIONAL_SHIPPING,
            limit=5,
        )
    payload = out.model_dump(mode="json")
    json.dumps(payload)
    assert payload["query"] == QUERY_INTERNATIONAL_SHIPPING
    assert str(bot_main) == payload["bot_id"]
    assert len(payload["hits"]) == 2
    assert payload["context_meta"] is not None
    assert payload["context_meta"]["chunks_in_context"] <= payload["context_meta"]["chunks_retrieved"]
    assert len(payload["context"]) <= len(payload["hits"])
    for h in payload["hits"]:
        assert h["chunk_id"]
        assert h["knowledge_file_id"]
        assert isinstance(h["chunk_index"], int)
        assert len(h["content"]) > 20
        assert isinstance(h["rank"], (int, float))
        assert h["page_number"] is not None
        assert h["original_filename"].endswith(".pdf")
    for c in payload["context"]:
        assert "estimated_tokens" in c
        assert c["content"]