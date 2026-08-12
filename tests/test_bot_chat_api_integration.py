"""
AI chat dashboard API integration tests (PostgreSQL + HTTP; fake provider, no live Gemini).

Covers owner/non-owner scoping, successful assistant payload, conversation fetch, and
provider-failure → structured errors without traceback leaks.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from fastapi.testclient import TestClient

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_bot_chat_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


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


def _unique_email(prefix: str = "chat-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Chat API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access: str, *, name: str = "Chat Test Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": name,
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


class _FakeProviderOk(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        assert len(params.messages) >= 1
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


class _FakeProviderFail(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=False,
            provider_name="gemini",
            text=None,
            model_name=params.model,
            error_code="rate_limited",
            error_message="Too many requests; try later.",
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


class _FakeProviderTimeout(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=False,
            provider_name="gemini",
            text=None,
            model_name=params.model,
            error_code="timeout",
            error_message=None,
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


class _FakeProviderAuthFailed(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=False,
            provider_name="gemini",
            text=None,
            model_name=params.model,
            error_code="auth_failed",
            error_message=None,
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


class _FakeProviderEmptyCompletion(AIProvider):
    """Provider returns success with no usable text → normalized to invalid_response in AIService."""

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-integration-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="",
            model_name=params.model,
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


def _assert_no_traceback_leak(body_text: str) -> None:
    lower = body_text.lower()
    assert "traceback" not in lower
    assert "  File " not in body_text
    assert "  File '" not in body_text


def test_owner_can_post_test_chat_and_response_is_clean(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    access = _register_and_get_access(chat_client, _unique_email("owner-chat"))
    bot_id = _create_bot(chat_client, access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "Hello from integration test"},
    )
    assert r.status_code == 200, r.text
    _assert_no_traceback_leak(r.text)
    data = r.json()
    assert data["assistant_text"] == "Integration assistant reply."
    assert data["conversation_id"]
    assert data["user_message_id"]
    assert data["assistant_message_id"]
    assert data.get("latency_ms") is not None
    assert data.get("tokens_total") is not None


def test_non_owner_cannot_post_test_chat(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    owner_access = _register_and_get_access(chat_client, _unique_email("owner-scoped"))
    other_access = _register_and_get_access(chat_client, _unique_email("intruder"))
    bot_id = _create_bot(chat_client, owner_access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(other_access),
        json={"message": "Unauthorized attempt"},
    )
    assert r.status_code == 403, r.text
    _assert_no_traceback_leak(r.text)
    err = r.json().get("error", {})
    assert err.get("code") == "ai_forbidden"
    assert err.get("category") == "ai_chat"


def test_owner_can_fetch_conversation_after_test_chat(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    access = _register_and_get_access(chat_client, _unique_email("owner-conv"))
    bot_id = _create_bot(chat_client, access)

    post = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "First line"},
    )
    assert post.status_code == 200, post.text
    conv_id = post.json()["conversation_id"]

    get = chat_client.get(
        f"/api/v1/bots/{bot_id}/conversations/{conv_id}",
        headers=_auth_headers(access),
    )
    assert get.status_code == 200, get.text
    _assert_no_traceback_leak(get.text)
    payload = get.json()
    assert payload["conversation"]["id"] == conv_id
    assert payload["conversation"]["bot_id"] == bot_id
    roles = [m["role"] for m in payload["messages"]]
    assert "user" in roles and "assistant" in roles
    assistant_msgs = [m for m in payload["messages"] if m["role"] == "assistant"]
    assert any(m["content"] == "Integration assistant reply." for m in assistant_msgs)


def test_non_owner_cannot_fetch_conversation(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    owner_access = _register_and_get_access(chat_client, _unique_email("conv-owner"))
    other_access = _register_and_get_access(chat_client, _unique_email("conv-other"))
    bot_id = _create_bot(chat_client, owner_access)

    post = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(owner_access),
        json={"message": "secret thread"},
    )
    assert post.status_code == 200, post.text
    conv_id = post.json()["conversation_id"]

    get = chat_client.get(
        f"/api/v1/bots/{bot_id}/conversations/{conv_id}",
        headers=_auth_headers(other_access),
    )
    assert get.status_code == 403, get.text
    _assert_no_traceback_leak(get.text)


def test_provider_timeout_maps_to_clean_api_error(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderTimeout(),
    )
    access = _register_and_get_access(chat_client, _unique_email("timeout-map"))
    bot_id = _create_bot(chat_client, access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "Will time out"},
    )
    assert r.status_code == 504, r.text
    _assert_no_traceback_leak(r.text)
    err = r.json().get("error", {})
    assert err.get("code") == "ai_timeout"
    assert err.get("ai_category") == "timeout"
    assert err.get("details", {}).get("retryable") is True


def test_provider_auth_config_maps_to_clean_api_error(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderAuthFailed(),
    )
    access = _register_and_get_access(chat_client, _unique_email("auth-map"))
    bot_id = _create_bot(chat_client, access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "Bad key"},
    )
    assert r.status_code == 502, r.text
    _assert_no_traceback_leak(r.text)
    err = r.json().get("error", {})
    assert err.get("code") == "ai_auth_config"
    assert err.get("ai_category") == "auth_config"
    assert err.get("details", {}).get("retryable") is False


def test_after_provider_failure_transcript_has_user_turn_without_assistant(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MVP: user message is persisted before the provider; failed completion does not add an assistant row."""
    access = _register_and_get_access(chat_client, _unique_email("mvp-consistency"))
    bot_id = _create_bot(chat_client, access)

    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    first = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "seed thread"},
    )
    assert first.status_code == 200, first.text
    conv_id = first.json()["conversation_id"]

    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderTimeout(),
    )
    fail = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "second user turn", "conversation_id": conv_id},
    )
    assert fail.status_code == 504, fail.text
    _assert_no_traceback_leak(fail.text)

    get = chat_client.get(
        f"/api/v1/bots/{bot_id}/conversations/{conv_id}",
        headers=_auth_headers(access),
    )
    assert get.status_code == 200, get.text
    msgs = get.json()["messages"]
    roles = [m["role"] for m in msgs]
    assert roles.count("user") == 2
    assert roles.count("assistant") == 1
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "second user turn"


def test_invalid_provider_response_empty_completion_maps_cleanly(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderEmptyCompletion(),
    )
    access = _register_and_get_access(chat_client, _unique_email("empty-completion"))
    bot_id = _create_bot(chat_client, access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "ping"},
    )
    assert r.status_code == 502, r.text
    _assert_no_traceback_leak(r.text)
    err = r.json().get("error", {})
    assert err.get("code") == "ai_invalid_provider_response"
    assert err.get("ai_category") == "invalid_provider_response"


def test_provider_failure_maps_to_clean_api_error(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderFail(),
    )
    access = _register_and_get_access(chat_client, _unique_email("fail-map"))
    bot_id = _create_bot(chat_client, access)

    r = chat_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(access),
        json={"message": "This will rate-limit"},
    )
    assert r.status_code == 429, r.text
    _assert_no_traceback_leak(r.text)
    body = r.json()
    err = body.get("error", {})
    assert err.get("code") == "ai_rate_limited"
    assert err.get("category") == "ai_chat"
    assert err.get("ai_category") == "provider_unavailable"
    assert err.get("details", {}).get("provider_error_code") == "rate_limited"
    assert err.get("details", {}).get("retryable") is True
    # Stable JSON shape only — no exception type dumps
    dumped = json.dumps(body)
    assert "RuntimeError" not in dumped
    assert "NormalizedAIResult" not in dumped


def test_unknown_conversation_returns_404_not_traceback(
    chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )
    access = _register_and_get_access(chat_client, _unique_email("nf-conv"))
    bot_id = _create_bot(chat_client, access)
    fake_conv = str(uuid.uuid4())

    r = chat_client.get(
        f"/api/v1/bots/{bot_id}/conversations/{fake_conv}",
        headers=_auth_headers(access),
    )
    assert r.status_code == 404, r.text
    _assert_no_traceback_leak(r.text)
    assert r.json().get("error", {}).get("code") == "ai_not_found"
