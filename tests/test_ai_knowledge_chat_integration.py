"""
End-to-end AI chat + knowledge retrieval (PostgreSQL, HTTP, mocked provider).

Exercises :class:`~app.services.ai_service.AIService` via ``POST /bots/{id}/chat/test`` with real
``KnowledgeRetrievalService`` / DB, while the LLM provider is replaced by a fake that captures
``GenerateParams``.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import get_settings
from app.core.db import dispose_engine, normalize_database_url
from app.main import app
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.db_alembic import run_alembic_upgrade_head
from tests.fixtures.knowledge_retrieval_samples import (
    CHUNK_INTL_SHIPPING_DENSE,
    CHUNK_OTHER_BOT_DECOY,
    QUERY_INTERNATIONAL_SHIPPING,
)
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.ai_knowledge_chat,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _is_db_unreachable(exc: BaseException) -> bool:
    """Host/Docker networking issues often surface as OSError or asyncpg-specific errors."""
    if isinstance(exc, (OSError, ConnectionError, OperationalError)):
        return True
    mod = getattr(exc.__class__, "__module__", "")
    return mod == "asyncpg.exceptions"


@pytest.fixture(scope="module", autouse=True)
def _alembic_ai_knowledge_chat() -> None:
    url = _integration_db_url()
    if not url:
        return
    try:
        run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)
    except BaseException as exc:
        if _is_db_unreachable(exc):
            pytest.skip(f"Integration PostgreSQL unreachable (alembic upgrade failed): {exc}")
        raise


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def chat_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register_and_create_bot(client: TestClient, *, prefix: str = "ak") -> tuple[uuid.UUID, uuid.UUID, str]:
    email = f"{prefix}_{uuid.uuid4().hex}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "AI Knowledge Chat"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    user_id = uuid.UUID(data["user"]["id"])
    access = str(data["access_token"])
    r2 = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": f"Bot {prefix}",
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert r2.status_code == 201, r2.text
    bot_id = uuid.UUID(r2.json()["id"])
    return user_id, bot_id, access


async def _insert_ready_knowledge_ephemeral(
    db_url: str,
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID,
    original_filename: str,
    chunks: list[tuple[int, str, int, int | None]],
) -> None:
    """
    Insert via a short-lived engine so we do not share asyncpg connections with
    :class:`TestClient` (different asyncio loops).

    ``chunks``: ``(chunk_index, content, token_count, page_number)``.
    """
    file_id = uuid.uuid4()
    engine = create_async_engine(normalize_database_url(db_url), pool_pre_ping=True)
    try:
        sm = async_sessionmaker(engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
        async with sm() as session:
            kf = KnowledgeFile(
                id=file_id,
                bot_id=bot_id,
                owner_id=owner_id,
                original_filename=original_filename,
                storage_key=f"v1/k/{file_id}.pdf",
                mime_type="application/pdf",
                file_size_bytes=100,
                processing_status="ready",
            )
            session.add(kf)
            for idx, content, tok, page in chunks:
                session.add(
                    KnowledgeChunk(
                        knowledge_file_id=file_id,
                        bot_id=bot_id,
                        owner_id=owner_id,
                        chunk_index=idx,
                        page_number=page,
                        content=content,
                        token_count=tok,
                    ),
                )
            await session.commit()
    finally:
        await engine.dispose()


def _insert_ready_knowledge(
    db_url: str,
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID,
    original_filename: str,
    chunks: list[tuple[int, str, int, int | None]],
) -> None:
    asyncio.run(
        _insert_ready_knowledge_ephemeral(
            db_url,
            owner_id=owner_id,
            bot_id=bot_id,
            original_filename=original_filename,
            chunks=chunks,
        ),
    )


async def _seed_cross_bot_corpus_ephemeral(
    db_url: str,
    *,
    user_id: uuid.UUID,
    bot_main: uuid.UUID,
    bot_other: uuid.UUID,
) -> None:
    file_main = uuid.uuid4()
    file_other = uuid.uuid4()
    engine = create_async_engine(normalize_database_url(db_url), pool_pre_ping=True)
    try:
        sm = async_sessionmaker(engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
        async with sm() as session:
            k_main = KnowledgeFile(
                id=file_main,
                bot_id=bot_main,
                owner_id=user_id,
                original_filename="Logistics_Guide.pdf",
                storage_key=f"v1/k/{file_main}.pdf",
                mime_type="application/pdf",
                file_size_bytes=50_000,
                processing_status="ready",
            )
            k_other = KnowledgeFile(
                id=file_other,
                bot_id=bot_other,
                owner_id=user_id,
                original_filename="Enterprise_SLA.pdf",
                storage_key=f"v1/k/{file_other}.pdf",
                mime_type="application/pdf",
                file_size_bytes=12_000,
                processing_status="ready",
            )
            session.add_all(
                [
                    k_main,
                    k_other,
                    KnowledgeChunk(
                        knowledge_file_id=file_main,
                        bot_id=bot_main,
                        owner_id=user_id,
                        chunk_index=0,
                        page_number=2,
                        content=CHUNK_INTL_SHIPPING_DENSE,
                        token_count=40,
                    ),
                    KnowledgeChunk(
                        knowledge_file_id=file_other,
                        bot_id=bot_other,
                        owner_id=user_id,
                        chunk_index=0,
                        page_number=1,
                        content=CHUNK_OTHER_BOT_DECOY,
                        token_count=30,
                    ),
                ],
            )
            await session.commit()
    finally:
        await engine.dispose()


class _CapturingProviderOk(AIProvider):
    """Returns a fixed success payload and stores the last ``GenerateParams``."""

    def __init__(self) -> None:
        self.last_params: GenerateParams | None = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-knowledge-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        self.last_params = params
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="Integration assistant reply.",
            model_name=params.model,
            tokens=TokenUsage(input_tokens=2, output_tokens=3, total_tokens=5),
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


def _patch_provider(monkeypatch: pytest.MonkeyPatch, provider: _CapturingProviderOk) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None, _p=provider: _p,
    )


def _system_text(params: GenerateParams | None) -> str:
    assert params is not None
    sys_msgs = [m for m in params.messages if m.role == "system"]
    assert len(sys_msgs) == 1
    return sys_msgs[0].content


def _assert_clean_provider_messages(params: GenerateParams | None) -> None:
    assert params is not None
    assert len(params.messages) >= 2
    for m in params.messages:
        assert isinstance(m, ChatMessage)
        assert m.role in ("system", "user", "assistant")
        assert isinstance(m.content, str)


def test_chat_bot_without_knowledge_still_works(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _CapturingProviderOk()
    _patch_provider(monkeypatch, cap)
    _user_id, bot_id, access = _register_and_create_bot(chat_client, prefix="nokb")

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "Hello, any docs?"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assistant_text"] == "Integration assistant reply."
    kc = data.get("knowledge_context")
    assert kc is not None
    assert kc["had_ready_knowledge_files"] is False
    _assert_clean_provider_messages(cap.last_params)
    assert "uploaded knowledge files" not in _system_text(cap.last_params).lower()


def test_chat_bot_with_knowledge_injects_retrieved_context(
    chat_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _CapturingProviderOk()
    _patch_provider(monkeypatch, cap)
    user_id, bot_id, access = _register_and_create_bot(chat_client, prefix="withkb")
    # Space-separated tokens so PostgreSQL ``simple`` + ``websearch_to_tsquery`` match reliably.
    marker = "k7uniqrefundsnippet99"
    _insert_ready_knowledge(
        live_db_url,
        owner_id=user_id,
        bot_id=bot_id,
        original_filename="Policy_Handbook.pdf",
        chunks=[
            (0, f"Returns and refunds: use code {marker} for policy details on all orders.", 50, 1),
        ],
    )

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": f"refunds policy {marker}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assistant_text"] == "Integration assistant reply."
    kc = data["knowledge_context"]
    assert kc["had_ready_knowledge_files"] is True
    assert kc["retrieval_hit_count"] >= 1
    assert kc["context_chunk_count"] >= 1

    sys_t = _system_text(cap.last_params)
    assert marker in sys_t
    assert "Policy_Handbook.pdf" in sys_t
    assert "uploaded knowledge files" in sys_t.lower()
    _assert_clean_provider_messages(cap.last_params)


def test_chat_no_retrieval_hits_still_succeeds(
    chat_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _CapturingProviderOk()
    _patch_provider(monkeypatch, cap)
    user_id, bot_id, access = _register_and_create_bot(chat_client, prefix="nohit")
    _insert_ready_knowledge(
        live_db_url,
        owner_id=user_id,
        bot_id=bot_id,
        original_filename="Solar_Manual.pdf",
        chunks=[
            (0, "Solar panel efficiency peaks at noon under direct sunlight.", 40, 1),
        ],
    )

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "zzzquantum_laser_no_match_xyzzy_999"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assistant_text"] == "Integration assistant reply."
    kc = data["knowledge_context"]
    assert kc["had_ready_knowledge_files"] is True
    assert kc["context_chunk_count"] == 0

    sys_t = _system_text(cap.last_params)
    assert "Solar panel efficiency" not in sys_t
    assert "uploaded knowledge files" not in sys_t.lower()
    _assert_clean_provider_messages(cap.last_params)


def test_cost_aware_context_selection_respects_chunk_cap(
    chat_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KNOWLEDGE_CONTEXT_DEFAULT_MAX_CHUNKS", "1")
    get_settings.cache_clear()

    cap = _CapturingProviderOk()
    _patch_provider(monkeypatch, cap)
    user_id, bot_id, access = _register_and_create_bot(chat_client, prefix="budget")
    first_only = "FIRST_CHUNK_ONLY_MARKER_budget_ctx"
    second_only = "SECOND_CHUNK_SHOULD_NOT_APPEAR_budget_ctx"
    _insert_ready_knowledge(
        live_db_url,
        owner_id=user_id,
        bot_id=bot_id,
        original_filename="Budget_Guide.pdf",
        chunks=[
            (
                0,
                ("budget_ctx_keyword " * 25) + first_only,
                120,
                1,
            ),
            (
                1,
                "budget_ctx_keyword once " + second_only,
                80,
                2,
            ),
        ],
    )

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "budget_ctx_keyword"},
    )
    assert r.status_code == 200, r.text
    kc = r.json()["knowledge_context"]
    assert kc["context_chunk_count"] == 1

    sys_t = _system_text(cap.last_params)
    assert first_only in sys_t
    assert second_only not in sys_t
    _assert_clean_provider_messages(cap.last_params)


def test_no_cross_bot_knowledge_leakage(
    chat_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = _CapturingProviderOk()
    _patch_provider(monkeypatch, cap)
    email = f"xb_{uuid.uuid4().hex}@example.com"
    reg = chat_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Cross Bot"},
    )
    assert reg.status_code == 201, reg.text
    user_id = uuid.UUID(reg.json()["user"]["id"])
    access = str(reg.json()["access_token"])
    hdr = _auth_headers(access)

    r_main = chat_client.post(
        "/api/v1/bots",
        headers=hdr,
        json={"name": "Main", "niche_id": "education", "goal_type": "support"},
    )
    r_other = chat_client.post(
        "/api/v1/bots",
        headers=hdr,
        json={"name": "Other", "niche_id": "education", "goal_type": "support"},
    )
    assert r_main.status_code == 201 and r_other.status_code == 201
    bot_main = uuid.UUID(r_main.json()["id"])
    bot_other = uuid.UUID(r_other.json()["id"])

    asyncio.run(_seed_cross_bot_corpus_ephemeral(live_db_url, user_id=user_id, bot_main=bot_main, bot_other=bot_other))

    r = chat_client.post(
        f"/api/v1/bots/{bot_main}/chat/test",
        headers=hdr,
        json={"message": QUERY_INTERNATIONAL_SHIPPING},
    )
    assert r.status_code == 200, r.text
    sys_t = _system_text(cap.last_params)
    assert "International shipping routes" in sys_t or "checkout" in sys_t.lower()
    assert "dedicated customs brokers" not in sys_t
    assert "enterprise accounts" not in sys_t.lower()
    _assert_clean_provider_messages(cap.last_params)
