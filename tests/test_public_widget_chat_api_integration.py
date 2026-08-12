"""
Public widget chat runtime — integration tests (PostgreSQL + HTTP + fake provider).

Checklist:
  1. Valid widget accepts a public message
  2. AI path returns assistant text and message ids
  3. Disabled widget is blocked
  4. Invalid widget key is rejected
  5. Session continuity across turns (key + id, and key-only)
  6. Owner / dashboard internals are not exposed in JSON
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
from app.core.public_widget_abuse import reset_public_widget_abuse_memory_for_tests
from app.main import app
from fastapi.testclient import TestClient

from tests.integration_db import integration_database_url
from tests.public_widget_paths import public_widget_chat_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32

_ALLOWED_PUBLIC_CHAT_TOP_LEVEL_KEYS = frozenset(
    {
        "conversation_id",
        "visitor_session_key",
        "user_message_id",
        "assistant_message_id",
        "assistant_text",
        "bot_display_name",
    },
)

# Must not appear as any object key in a successful chat JSON (or nested error details we control).
_BANNED_KEYS_ANYWHERE = frozenset(
    {
        "owner_id",
        "bot_id",
        "user_id",
        "email",
        "password",
        "cost_usd",
        "model_name",
        "provider_name",
        "knowledge_context",
        "tokens_input",
        "tokens_output",
        "tokens_total",
        "niche_id",
        "goal_type",
        "public_widget_key",
        "allowed_domains",
        "allowed_domains_json",
        "widget_settings",
        "widget_settings_json",
        "access_token",
        "refresh_token",
    },
)


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
def _alembic_for_public_widget_chat_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def pub_chat_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "pub-chat") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Pub Chat"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str, *, name: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={
            "name": name,
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _walk_json_keys(obj: object, visitor: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            visitor.add(str(k))
            _walk_json_keys(v, visitor)
    elif isinstance(obj, list):
        for x in obj:
            _walk_json_keys(x, visitor)


def _assert_no_banned_keys_in_json(obj: object) -> None:
    keys: set[str] = set()
    _walk_json_keys(obj, keys)
    leaked = keys & _BANNED_KEYS_ANYWHERE
    assert not leaked, f"Unexpected keys in public chat JSON: {leaked}"


def _assert_success_chat_has_only_public_fields(data: dict) -> None:
    assert set(data.keys()) == _ALLOWED_PUBLIC_CHAT_TOP_LEVEL_KEYS
    _assert_no_banned_keys_in_json(data)


class _FakeProviderOk(AIProvider):
    reply_text: str = "Widget visitor reply."

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


def _patch_fake_provider(monkeypatch: pytest.MonkeyPatch, *, reply_text: str = "Widget visitor reply.") -> None:
    def _resolver(_settings, _provider_id=None):
        p = _FakeProviderOk()
        p.reply_text = reply_text
        return p

    monkeypatch.setattr("app.services.ai_service.resolve_ai_provider", _resolver)


def _widget_setup(client: TestClient, *, name: str = "Widget Chat Bot") -> tuple[str, str]:
    access = _register_and_get_access(client, _unique_email())
    bot_id = _create_bot(client, access, name=name)
    w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
    assert w.status_code == 200, w.text
    public_key = str(w.json()["public_widget_key"])
    return public_key, bot_id


# --- Runtime checklist (integration) ---


def test_valid_widget_accepts_public_message(pub_chat_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_setup(pub_chat_client)

    r = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "Hello from visitor"})
    assert r.status_code == 200, r.text


def test_ai_response_returns_correctly(pub_chat_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_provider(monkeypatch, reply_text="Custom assistant line for widget.")
    public_key, _ = _widget_setup(pub_chat_client)

    r = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "Question?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assistant_text"] == "Custom assistant line for widget."
    uuid.UUID(str(data["user_message_id"]))
    uuid.UUID(str(data["assistant_message_id"]))
    uuid.UUID(str(data["conversation_id"]))
    assert data["bot_display_name"] == "Widget Chat Bot"


def test_disabled_widget_chat_is_blocked(pub_chat_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fake_provider(monkeypatch)
    access = _register_and_get_access(pub_chat_client, _unique_email("disabled-chat"))
    bot_id = _create_bot(pub_chat_client, access, name="Soon Disabled")
    w = pub_chat_client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
    public_key = str(w.json()["public_widget_key"])

    off = pub_chat_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"is_enabled": False},
    )
    assert off.status_code == 200, off.text

    r = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "Should not run"})
    assert r.status_code == 403, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "widget_disabled"
    assert "owner" not in err.get("message", "").lower()


def test_invalid_widget_key_rejected(pub_chat_client: TestClient) -> None:
    r = pub_chat_client.post(public_widget_chat_path("x" * 43), json={"message": "Hi"})
    assert r.status_code == 404, r.text
    assert r.json().get("error", {}).get("code") == "widget_not_found"


def test_session_continuity_with_visitor_key_and_conversation_id(
    pub_chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_setup(pub_chat_client)

    first = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "Turn one"})
    assert first.status_code == 200, first.text
    vk = first.json()["visitor_session_key"]
    cid = first.json()["conversation_id"]

    second = pub_chat_client.post(
        public_widget_chat_path(public_key),
        json={"message": "Turn two", "visitor_session_key": vk, "conversation_id": cid},
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["conversation_id"] == cid
    assert body["visitor_session_key"] == vk
    assert body["user_message_id"] != first.json()["user_message_id"]
    assert body["assistant_message_id"] != first.json()["assistant_message_id"]


def test_session_continuity_with_visitor_key_only_on_second_turn(
    pub_chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second POST omits conversation_id; server resolves thread from visitor_session_key alone."""
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_setup(pub_chat_client)

    first = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "First"})
    assert first.status_code == 200, first.text
    vk = first.json()["visitor_session_key"]
    cid = first.json()["conversation_id"]

    second = pub_chat_client.post(
        public_widget_chat_path(public_key),
        json={"message": "Second", "visitor_session_key": vk},
    )
    assert second.status_code == 200, second.text
    assert second.json()["conversation_id"] == cid
    assert second.json()["visitor_session_key"] == vk


def test_owner_and_dashboard_data_not_exposed_in_chat_response(
    pub_chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe_email = f"ownerprobe_{uuid.uuid4().hex}@leakcheck.example"
    _patch_fake_provider(monkeypatch)
    access = _register_and_get_access(pub_chat_client, probe_email)
    bot_id = _create_bot(pub_chat_client, access, name="Leak Check Bot")
    w = pub_chat_client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
    public_key = str(w.json()["public_widget_key"])

    r = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "Hi"})
    assert r.status_code == 200, r.text
    raw = r.text
    assert probe_email.lower() not in raw.lower()
    assert "password" not in raw.lower()
    data = r.json()
    _assert_success_chat_has_only_public_fields(data)
    # Full document must not smuggle extra top-level keys
    parsed = json.loads(raw)
    assert set(parsed.keys()) == _ALLOWED_PUBLIC_CHAT_TOP_LEVEL_KEYS


def test_wrong_conversation_id_for_session_returns_403(
    pub_chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_setup(pub_chat_client)

    first = pub_chat_client.post(public_widget_chat_path(public_key), json={"message": "One"})
    vk = first.json()["visitor_session_key"]

    bad = pub_chat_client.post(
        public_widget_chat_path(public_key),
        json={"message": "nope", "visitor_session_key": vk, "conversation_id": str(uuid.uuid4())},
    )
    assert bad.status_code == 403, bad.text
    assert bad.json().get("error", {}).get("code") == "public_widget_conversation_mismatch"


def test_allowlist_enforced_on_chat(
    pub_chat_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_provider(monkeypatch)
    access = _register_and_get_access(pub_chat_client, _unique_email("allow"))
    bot_id = _create_bot(pub_chat_client, access, name="Allow Bot")
    w = pub_chat_client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
    public_key = str(w.json()["public_widget_key"])

    pub_chat_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"allowed_domains_json": ["chat.embed.test"]},
    )

    denied = pub_chat_client.post(
        public_widget_chat_path(public_key),
        headers={"Origin": "https://evil.test"},
        json={"message": "Hi"},
    )
    assert denied.status_code == 403, denied.text
    assert denied.json().get("error", {}).get("code") == "widget_origin_forbidden"

    ok = pub_chat_client.post(
        public_widget_chat_path(public_key),
        headers={"Origin": "https://chat.embed.test"},
        json={"message": "Hi"},
    )
    assert ok.status_code == 200, ok.text


def test_conversation_id_without_visitor_key_returns_422(pub_chat_client: TestClient) -> None:
    public_key, _ = _widget_setup(pub_chat_client)
    r = pub_chat_client.post(
        public_widget_chat_path(public_key),
        json={"message": "Hi", "conversation_id": str(uuid.uuid4())},
    )
    assert r.status_code == 422, r.text


# --- Anti-abuse safeguards (integration, E2E HTTP) ---


def _client_with_abuse_env(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    return TestClient(app)


def test_public_widget_chat_abuse_session_burst_returns_safe_429(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    """Tight session burst → 429 with generic envelope, Retry-After, no internal reason strings."""
    reset_public_widget_abuse_memory_for_tests()
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_SESSION_BURST_PER_MINUTE", "2")
    monkeypatch.setenv("APP_RATE_LIMIT_PUBLIC_WIDGET_CHAT_PER_MINUTE", "100")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_IDENTICAL_TOTAL_PER_WINDOW", "0")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_MAX_CONSECUTIVE_IDENTICAL", "0")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_MAX_MESSAGE_CHARS", "0")
    client = _client_with_abuse_env(monkeypatch, live_db_url)
    try:
        _patch_fake_provider(monkeypatch)
        public_key, _ = _widget_setup(client)
        r1 = client.post(public_widget_chat_path(public_key), json={"message": "one"})
        assert r1.status_code == 200, r1.text
        vk = r1.json()["visitor_session_key"]
        cid = r1.json()["conversation_id"]
        r2 = client.post(
            public_widget_chat_path(public_key),
            json={"message": "two", "visitor_session_key": vk, "conversation_id": cid},
        )
        assert r2.status_code == 200, r2.text
        r3 = client.post(
            public_widget_chat_path(public_key),
            json={"message": "three", "visitor_session_key": vk, "conversation_id": cid},
        )
        assert r3.status_code == 429, r3.text
        err = r3.json().get("error", {})
        assert err.get("code") == "rate_limit_exceeded"
        assert err.get("category") is None
        assert "session_burst" not in r3.text.lower()
        assert "identical" not in r3.text.lower()
        assert r3.headers.get("retry-after") == "60"
    finally:
        client.close()
        asyncio.run(dispose_engine())
        get_settings.cache_clear()


def test_public_widget_chat_abuse_oversize_message_returns_safe_400(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    reset_public_widget_abuse_memory_for_tests()
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_MAX_MESSAGE_CHARS", "80")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_SESSION_BURST_PER_MINUTE", "20")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_IDENTICAL_TOTAL_PER_WINDOW", "0")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ABUSE_MAX_CONSECUTIVE_IDENTICAL", "0")
    client = _client_with_abuse_env(monkeypatch, live_db_url)
    try:
        public_key, _ = _widget_setup(client)
        r = client.post(public_widget_chat_path(public_key), json={"message": "z" * 81})
        assert r.status_code == 400, r.text
        assert "too long" in r.json().get("error", {}).get("message", "").lower()
        assert "widget_key_digest" not in r.text.lower()
        assert "sha256" not in r.text.lower()
    finally:
        client.close()
        asyncio.run(dispose_engine())
        get_settings.cache_clear()
