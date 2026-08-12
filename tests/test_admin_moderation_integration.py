"""
Superadmin moderation API integration tests (PostgreSQL + JWT).

Covers suspend/activate users and bots, audit rows, non-superadmin denial, and runtime enforcement
(widget bootstrap/chat, dashboard test chat).

Run: ``pytest tests/test_admin_moderation_integration.py -m integration -v``
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit_service import (
    BOT_ACTION_PLATFORM_SUSPENDED,
    BOT_ACTION_PLATFORM_UNSUSPENDED,
    USER_ACTION_SUSPENDED,
    USER_ACTION_UNSUSPENDED,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from tests.integration_db import integration_database_url
from tests.public_widget_paths import public_widget_bootstrap_path, public_widget_chat_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_MOD_KEY = "x" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
            "(not @postgres: from host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    import os

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
def _alembic_for_admin_moderation() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def mod_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_MOD_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-moderation-test-key")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "mod") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Mod Test"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str, *, name: str = "Mod Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={"name": name, "niche_id": "generic", "goal_type": "faq"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _widget_public_key(client: TestClient, access_token: str, bot_id: str) -> str:
    w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access_token))
    assert w.status_code == 200, w.text
    return str(w.json()["public_widget_key"])


async def _promote_to_superadmin(user_id: uuid.UUID, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_MOD_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        await session.execute(update(User).where(User.id == user_id).values(role=UserRole.superadmin))
        await session.commit()


async def _audit_count(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    entity_id: uuid.UUID,
    action: str,
) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_MOD_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        n = await session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entity_id == entity_id,
                AuditLog.action == action,
            ),
        )
        return int(n or 0)


async def _latest_suspend_metadata(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    entity_id: uuid.UUID,
    action: str,
) -> dict | None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_MOD_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        row = await session.scalar(
            select(AuditLog.metadata_json)
            .where(AuditLog.entity_id == entity_id, AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(1),
        )
        return row if isinstance(row, dict) else None


class _FakeProviderOk(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-moderation-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="Moderation test reply.",
            model_name=params.model,
            tokens=TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3),
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


def _make_superadmin(mod_client: TestClient, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> tuple[str, uuid.UUID]:
    sa_reg = _register(mod_client, _unique_email("sa"))
    sa_token = sa_reg["access_token"]
    sa_id = uuid.UUID(sa_reg["user"]["id"])
    asyncio.run(_promote_to_superadmin(sa_id, live_db_url, monkeypatch))
    return sa_token, sa_id


# --- Checklist: superadmin moderation APIs ---


def test_superadmin_can_suspend_user(mod_client: TestClient, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    victim = _register(mod_client, _unique_email("suspend_u"))
    victim_id = uuid.UUID(victim["user"]["id"])
    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)

    r = mod_client.post(
        f"/api/v1/admin/users/{victim_id}/suspend",
        headers=_auth_headers(sa_token),
        json={"reason": "policy"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False
    assert r.json()["suspended_at"] is not None


def test_superadmin_can_activate_user(mod_client: TestClient, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    victim = _register(mod_client, _unique_email("activate_u"))
    victim_id = uuid.UUID(victim["user"]["id"])
    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)

    mod_client.post(
        f"/api/v1/admin/users/{victim_id}/suspend",
        headers=_auth_headers(sa_token),
        json={},
    )
    r = mod_client.post(
        f"/api/v1/admin/users/{victim_id}/activate",
        headers=_auth_headers(sa_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is True
    assert r.json()["suspended_at"] is None


def test_superadmin_can_suspend_bot(mod_client: TestClient, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = _register(mod_client, _unique_email("suspend_b_owner"))
    bot_id = uuid.UUID(_create_bot(mod_client, owner["access_token"]))
    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)

    r = mod_client.post(
        f"/api/v1/admin/bots/{bot_id}/suspend",
        headers=_auth_headers(sa_token),
        json={"reason": "tos"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["platform_suspended_at"] is not None


def test_superadmin_can_activate_bot(mod_client: TestClient, live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    owner = _register(mod_client, _unique_email("activate_b_owner"))
    bot_id = uuid.UUID(_create_bot(mod_client, owner["access_token"]))
    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)

    mod_client.post(
        f"/api/v1/admin/bots/{bot_id}/suspend",
        headers=_auth_headers(sa_token),
        json={},
    )
    r = mod_client.post(
        f"/api/v1/admin/bots/{bot_id}/activate",
        headers=_auth_headers(sa_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["platform_suspended_at"] is None


# --- Audit + metadata ---


def test_moderation_actions_are_audited_with_snapshots(
    mod_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    victim = _register(mod_client, _unique_email("audit_u"))
    victim_id = uuid.UUID(victim["user"]["id"])
    sa_token, sa_id = _make_superadmin(mod_client, live_db_url, monkeypatch)

    mod_client.post(
        f"/api/v1/admin/users/{victim_id}/suspend",
        headers=_auth_headers(sa_token),
        json={"reason": "spam"},
    )
    assert asyncio.run(_audit_count(live_db_url, monkeypatch, entity_id=victim_id, action=USER_ACTION_SUSPENDED)) >= 1

    meta = asyncio.run(
        _latest_suspend_metadata(
            live_db_url,
            monkeypatch,
            entity_id=victim_id,
            action=USER_ACTION_SUSPENDED,
        ),
    )
    assert meta is not None
    assert meta.get("reason") == "spam"

    mod_client.post(f"/api/v1/admin/users/{victim_id}/activate", headers=_auth_headers(sa_token))
    assert (
        asyncio.run(_audit_count(live_db_url, monkeypatch, entity_id=victim_id, action=USER_ACTION_UNSUSPENDED)) >= 1
    )

    owner = _register(mod_client, _unique_email("audit_b_owner"))
    bot_id = uuid.UUID(_create_bot(mod_client, owner["access_token"]))
    mod_client.post(
        f"/api/v1/admin/bots/{bot_id}/suspend",
        headers=_auth_headers(sa_token),
        json={"reason": "abuse"},
    )
    assert (
        asyncio.run(_audit_count(live_db_url, monkeypatch, entity_id=bot_id, action=BOT_ACTION_PLATFORM_SUSPENDED)) >= 1
    )

    mod_client.post(f"/api/v1/admin/bots/{bot_id}/activate", headers=_auth_headers(sa_token))
    assert (
        asyncio.run(
            _audit_count(live_db_url, monkeypatch, entity_id=bot_id, action=BOT_ACTION_PLATFORM_UNSUSPENDED),
        )
        >= 1
    )

    async def _last_audit_actor(entity: uuid.UUID, action: str) -> uuid.UUID | None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        sm = get_session_maker()
        async with sm() as session:
            aid = await session.scalar(
                select(AuditLog.actor_user_id)
                .where(AuditLog.entity_id == entity, AuditLog.action == action)
                .order_by(AuditLog.created_at.desc())
                .limit(1),
            )
            return aid if aid else None

    assert asyncio.run(_last_audit_actor(victim_id, USER_ACTION_SUSPENDED)) == sa_id
    assert asyncio.run(_last_audit_actor(bot_id, BOT_ACTION_PLATFORM_SUSPENDED)) == sa_id


# --- Non-superadmin ---


def test_non_superadmin_cannot_call_moderation_endpoints(mod_client: TestClient) -> None:
    reg = _register(mod_client, _unique_email("cust_mod"))
    token = reg["access_token"]
    uid = uuid.uuid4()
    bid = uuid.uuid4()

    for method, path in (
        ("POST", f"/api/v1/admin/users/{uid}/suspend"),
        ("POST", f"/api/v1/admin/users/{uid}/activate"),
        ("POST", f"/api/v1/admin/bots/{bid}/suspend"),
        ("POST", f"/api/v1/admin/bots/{bid}/activate"),
    ):
        r = mod_client.request(method, path, headers=_auth_headers(token), json={})
        assert r.status_code == 403, f"{method} {path}: {r.text}"


def test_superadmin_cannot_suspend_self(
    mod_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sa_token, sa_id = _make_superadmin(mod_client, live_db_url, monkeypatch)
    r = mod_client.post(
        f"/api/v1/admin/users/{sa_id}/suspend",
        headers=_auth_headers(sa_token),
        json={},
    )
    assert r.status_code == 400


# --- Runtime: suspended owner ---


def test_runtime_suspended_user_blocks_login_and_public_widget(
    mod_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _register(mod_client, _unique_email("rt_owner"))
    owner_id = uuid.UUID(owner["user"]["id"])
    owner_token = owner["access_token"]
    bot_id = _create_bot(mod_client, owner_token)
    pk = _widget_public_key(mod_client, owner_token, bot_id)

    assert mod_client.get(public_widget_bootstrap_path(pk)).status_code == 200

    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)
    assert (
        mod_client.post(
            f"/api/v1/admin/users/{owner_id}/suspend",
            headers=_auth_headers(sa_token),
            json={"reason": "abuse"},
        ).status_code
        == 200
    )

    login = mod_client.post(
        "/api/v1/auth/login",
        json={"email": owner["user"]["email"], "password": "password123"},
    )
    assert login.status_code == 403
    assert login.json().get("code") == "inactive_user"

    boot = mod_client.get(public_widget_bootstrap_path(pk))
    assert boot.status_code == 403
    assert boot.json().get("code") == "widget_runtime_blocked"

    chat = mod_client.post(public_widget_chat_path(pk), json={"message": "hello"})
    assert chat.status_code == 503
    assert chat.json().get("code") == "public_widget_chat_unavailable"


# --- Runtime: platform-suspended bot ---


def test_runtime_platform_suspended_bot_blocks_widget_and_dashboard_test_chat(
    mod_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )

    owner = _register(mod_client, _unique_email("rt_bot_owner"))
    owner_token = owner["access_token"]
    bot_id = _create_bot(mod_client, owner_token)
    pk = _widget_public_key(mod_client, owner_token, bot_id)

    assert mod_client.get(public_widget_bootstrap_path(pk)).status_code == 200

    ok_chat = mod_client.post(public_widget_chat_path(pk), json={"message": "before suspend"})
    assert ok_chat.status_code == 200, ok_chat.text

    ok_test = mod_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(owner_token),
        json={"message": "dashboard before"},
    )
    assert ok_test.status_code == 200, ok_test.text

    sa_token, _ = _make_superadmin(mod_client, live_db_url, monkeypatch)
    assert (
        mod_client.post(
            f"/api/v1/admin/bots/{bot_id}/suspend",
            headers=_auth_headers(sa_token),
            json={"reason": "platform"},
        ).status_code
        == 200
    )

    boot = mod_client.get(public_widget_bootstrap_path(pk))
    assert boot.status_code == 403
    assert boot.json().get("code") == "widget_runtime_blocked"

    chat = mod_client.post(public_widget_chat_path(pk), json={"message": "after suspend"})
    assert chat.status_code == 403
    assert chat.json().get("code") == "public_widget_bot_suspended"

    dash = mod_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(owner_token),
        json={"message": "dashboard after"},
    )
    assert dash.status_code == 403
    assert dash.json().get("code") == "ai_bot_platform_suspended"

    assert (
        mod_client.post(f"/api/v1/admin/bots/{bot_id}/activate", headers=_auth_headers(sa_token)).status_code == 200
    )

    assert mod_client.get(public_widget_bootstrap_path(pk)).status_code == 200
    restored = mod_client.post(
        f"/api/v1/bots/{bot_id}/chat/test",
        headers=_auth_headers(owner_token),
        json={"message": "dashboard restored"},
    )
    assert restored.status_code == 200, restored.text
