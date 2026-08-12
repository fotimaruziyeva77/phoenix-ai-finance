"""
Security and regression tests for the MVP hardening layer.

Covers: HTTP security headers, admin route guards, AI quota behavior, public-widget error
sanitization, Gemini key transport hygiene, and error-tracking scrub patterns.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage
from app.api import deps as deps_mod
from app.core import error_tracking as et
from app.core.config import Settings, get_settings
from app.integrations.providers.gemini import GeminiProvider
from app.main import create_app
from app.models.enums import UserRole
from app.services.ai_exceptions import AIServiceQuotaExceededError
from app.services.ai_service import AIService
from fastapi.testclient import TestClient

from tests.test_ai_service import _bot, _FakeProvider, _make_chat_and_bots, _user


def test_security_headers_on_health_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/t")
    monkeypatch.setenv("GEMINI_API_KEY", "test-hard-key")
    monkeypatch.delenv("APP_SECURITY_ENABLE_HSTS", raising=False)
    monkeypatch.setenv("APP_SECURITY_ENABLE_HSTS", "false")
    get_settings.cache_clear()
    app = create_app()
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in r.headers
        assert r.headers.get("Strict-Transport-Security") is None
    finally:
        get_settings.cache_clear()


def test_hsts_header_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/t")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("APP_SECURITY_ENABLE_HSTS", "true")
    get_settings.cache_clear()
    app = create_app()
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert "max-age=" in (r.headers.get("Strict-Transport-Security") or "")
    finally:
        monkeypatch.delenv("APP_SECURITY_ENABLE_HSTS", raising=False)
        get_settings.cache_clear()


def test_admin_suspend_requires_superadmin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/t")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    app = create_app()
    ca = SimpleNamespace(id=uuid.uuid4(), role=UserRole.customer_admin)

    async def _fake_auth() -> SimpleNamespace:
        return ca

    app.dependency_overrides[deps_mod.require_authenticated_user] = _fake_auth
    try:
        with TestClient(app) as client:
            r = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/suspend", json={})
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
    assert r.status_code == 403
    body = r.json()
    assert body["error"]["code"] == "forbidden"
    assert "Superadmin" in body["error"]["message"] or "superadmin" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_ai_daily_token_quota_blocks_before_persist() -> None:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_daily_total_tokens_soft_cap_per_bot": 50,
            "ai_monthly_total_tokens_cap_per_owner": 2_000_000_000,
        }
    )
    quota = AsyncMock()
    quota.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=0)
    quota.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=50)
    u = _user()
    b = _bot(owner_id=u.id)
    conv_id = uuid.uuid4()
    user_mid = uuid.uuid4()
    chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=uuid.uuid4())
    bots.get_bot_by_id = AsyncMock(return_value=b)
    svc = AIService(chat, bots, settings=settings, usage_quota_repo=quota)
    with pytest.raises(AIServiceQuotaExceededError):
        await svc.send_bot_message(b, u, "hello quota")
    chat.add_message.assert_not_awaited()
    quota.sum_tokens_total_for_bot_on_utc_date.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_daily_token_quota_skipped_when_cap_zero() -> None:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_daily_total_tokens_soft_cap_per_bot": 0,
        }
    )
    quota = AsyncMock()
    quota.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=0)
    quota.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=999_999)
    u = _user()
    b = _bot(owner_id=u.id)
    conv_id = uuid.uuid4()
    user_mid = uuid.uuid4()
    asst_mid = uuid.uuid4()
    chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
    bots.get_bot_by_id = AsyncMock(return_value=b)

    ok = NormalizedAIResult(
        success=True,
        provider_name="gemini",
        text="ok",
        model_name="m",
        tokens=TokenUsage(total_tokens=3),
    )
    fake = _FakeProvider(ok)
    svc = AIService(
        chat,
        bots,
        settings=settings,
        provider_resolver=lambda s, _pid: fake,
        usage_quota_repo=quota,
    )
    out = await svc.send_bot_message(b, u, "hi")
    assert out.success is True
    quota.sum_tokens_total_for_bot_on_utc_date.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_daily_token_quota_skipped_without_repository() -> None:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
            "gemini_api_key": "k",
            "ai_daily_total_tokens_soft_cap_per_bot": 10,
            "ai_monthly_total_tokens_cap_per_owner": 2_000_000_000,
        }
    )
    u = _user()
    b = _bot(owner_id=u.id)
    conv_id = uuid.uuid4()
    user_mid = uuid.uuid4()
    asst_mid = uuid.uuid4()
    chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=asst_mid)
    bots.get_bot_by_id = AsyncMock(return_value=b)
    ok = NormalizedAIResult(success=True, provider_name="gemini", text="x", model_name="m", tokens=TokenUsage(1))
    fake = _FakeProvider(ok)
    svc = AIService(
        chat,
        bots,
        settings=settings,
        provider_resolver=lambda s, _pid: fake,
        usage_quota_repo=None,
    )
    out = await svc.send_bot_message(b, u, "hi")
    assert out.success is True


def test_public_widget_chat_quota_error_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/t")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    app = create_app()

    class _QuotaWidgetSvc:
        async def send_public_message(self, **kwargs: object) -> None:
            raise AIServiceQuotaExceededError()

    app.dependency_overrides[deps_mod.get_public_widget_chat_service] = lambda: _QuotaWidgetSvc()
    try:
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/public/widget/not-a-real-key/chat",
                json={"message": "hello"},
            )
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert r.status_code == 503
    data = r.json()
    err = data["error"]
    assert err["code"] == "public_widget_chat_unavailable"
    msg = (err.get("message") or "").lower()
    assert "quota" not in msg
    assert "token" not in msg


def test_gemini_generate_content_sends_api_key_in_header_not_url() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = {k.lower(): v for k, v in request.headers.items()}
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]},
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="https://gl.test/v1beta") as client:
            p = GeminiProvider(api_key="UNIT_TEST_SECRET_KEY", http_client=client)
            await p.generate_response(
                GenerateParams(
                    model="gemini-test",
                    messages=(ChatMessage(role="user", content="yo"),),
                )
            )
            await p.aclose()

    asyncio.run(run())
    url = str(seen.get("url", ""))
    assert "UNIT_TEST_SECRET_KEY" not in url
    hdrs = seen.get("headers") or {}
    assert hdrs.get("x-goog-api-key") == "UNIT_TEST_SECRET_KEY"


def test_error_tracking_scrub_redacts_goog_api_key_field() -> None:
    out = et._scrub_value({"X-Goog-Api-Key": "should-redact", "safe": 1})
    assert out["X-Goog-Api-Key"] == "[redacted]"
    assert out["safe"] == 1
