"""
Single-chain MVP verification: auth → bot → widget → knowledge PDF → admin chat → public widget → leads → health → superadmin.

Uses real PostgreSQL + HTTP (TestClient). Object storage is mocked (same contract as bot knowledge file tests).
The LLM provider is replaced with a deterministic fake so runs do not call Gemini.

Run:
  pytest tests/test_mvp_product_journey_integration.py -m "integration and mvp_journey" -v
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.core.public_widget_abuse import reset_public_widget_abuse_memory_for_tests
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import update

from tests.db_alembic import run_alembic_upgrade_head
from tests.integration_db import integration_database_url
from tests.public_widget_paths import public_widget_chat_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "p" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.mvp_journey,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
            "(not @postgres: from host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_mvp_journey() -> None:
    url = _integration_db_url()
    assert url is not None
    run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def mock_object_storage(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    storage = AsyncMock()
    storage.upload_file = AsyncMock()
    storage.delete_file = AsyncMock()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    return storage


@pytest.fixture
def mvp_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    mock_object_storage: AsyncMock,
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-mvp-placeholder-key")
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "mvp") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _pdf_body() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class _MvpFakeProvider(AIProvider):
    """Single deterministic line for both dashboard test chat and public widget."""

    reply_text = "MVP integration assistant reply."

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-mvp-journey"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text=self.reply_text,
            model_name=params.model,
            tokens=TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


def _patch_mvp_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    def _resolver(_settings, _provider_id=None):
        return _MvpFakeProvider()

    monkeypatch.setattr("app.services.ai_service.resolve_ai_provider", _resolver)


async def _promote_to_superadmin(user_id: uuid.UUID, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        await session.execute(update(User).where(User.id == user_id).values(role=UserRole.superadmin))
        await session.commit()


def test_mvp_critical_product_chain(
    mvp_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    mock_object_storage: AsyncMock,
) -> None:
    _patch_mvp_provider(monkeypatch)
    reset_public_widget_abuse_memory_for_tests()

    email = _unique_email("journey")
    reg = mvp_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "MVP Journey"},
    )
    assert reg.status_code == 201, reg.text
    payload = reg.json()
    token = str(payload["access_token"])
    user_id = uuid.UUID(payload["user"]["id"])

    me = mvp_client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email
    assert me.json()["role"] == "customer_admin"

    bots_empty = mvp_client.get("/api/v1/bots", headers=_auth_headers(token))
    assert bots_empty.status_code == 200, bots_empty.text
    assert "items" in bots_empty.json()

    create = mvp_client.post(
        "/api/v1/bots",
        headers=_auth_headers(token),
        json={
            "name": "MVP Chain Bot",
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = str(create.json()["id"])

    w_get = mvp_client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(token))
    assert w_get.status_code == 200, w_get.text
    public_key = str(w_get.json()["public_widget_key"])

    w_patch = mvp_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(token),
        json={
            "welcome_text": "Hi — MVP widget welcome.",
            "theme": "light",
            "is_enabled": True,
        },
    )
    assert w_patch.status_code == 200, w_patch.text
    assert w_patch.json().get("welcome_text") == "Hi — MVP widget welcome."

    up = mvp_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("mvp.pdf", _pdf_body(), "application/pdf")},
    )
    assert up.status_code == 201, up.text
    assert up.json()["original_filename"] == "mvp.pdf"
    mock_object_storage.upload_file.assert_awaited()

    chat = mvp_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(token),
        json={"message": "Admin sanity message"},
    )
    assert chat.status_code == 200, chat.text
    chat_body = chat.json()
    assert chat_body["assistant_text"] == _MvpFakeProvider.reply_text
    assert chat_body.get("conversation_id")

    pub = mvp_client.post(
        public_widget_chat_path(public_key),
        json={"message": "Visitor hello from MVP chain"},
    )
    assert pub.status_code == 200, pub.text
    pub_body = pub.json()
    assert pub_body["assistant_text"] == _MvpFakeProvider.reply_text
    assert pub_body.get("conversation_id")

    leads = mvp_client.get("/api/v1/leads", headers=_auth_headers(token))
    assert leads.status_code == 200, leads.text
    lj = leads.json()
    assert "items" in lj and "total" in lj
    assert isinstance(lj["items"], list)

    health = mvp_client.get("/api/v1/health")
    assert health.status_code == 200, health.text
    assert health.json() == {"status": "ok"}

    secured = mvp_client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert secured.headers.get("x-content-type-options") == "nosniff"

    asyncio.run(_promote_to_superadmin(user_id, live_db_url, monkeypatch))
    platform = mvp_client.get("/api/v1/admin/platform/session", headers=_auth_headers(token))
    assert platform.status_code == 200, platform.text
    assert platform.json()["role"] == "superadmin"
    assert platform.json()["user_id"] == str(user_id)
