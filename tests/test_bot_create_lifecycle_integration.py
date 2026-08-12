"""
Bot create lifecycle: initial_channel, channel_pending, Telegram token enforcement (mocked Telegram).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.api.deps import get_telegram_config_service
from app.core.config import Settings, get_settings
from app.core.db import dispose_engine
from app.integrations.telegram_bot_verify import TelegramBotVerificationResult, TelegramTokenVerificationError
from app.main import app
from app.repositories.bot_repository import BotRepository
from app.services.telegram_config_service import TelegramConfigService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32
PUBLIC_API_BASE_INTEGRATION = "https://api.integration.test"
API_TOKEN = "123456789:AAH_bot_create_lifecycle_integration_xx"


async def _noop_set_webhook(_token: str, url: str, _secret: str) -> None:
    assert url.startswith(PUBLIC_API_BASE_INTEGRATION)


async def _noop_delete_webhook(_token: str) -> None:
    pass


async def _mock_verify_telegram_token(token: str) -> TelegramBotVerificationResult:
    if "___BAD___" in token:
        raise TelegramTokenVerificationError("bad")
    return TelegramBotVerificationResult(
        telegram_bot_id=888001,
        username="lifecycle_bot",
        first_name="LC",
    )


def _settings_for_dep() -> Settings:
    return get_settings()


def _override_telegram_config_service(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(_settings_for_dep),
) -> TelegramConfigService:
    return TelegramConfigService(
        session,
        BotRepository(session),
        settings,
        verify_token=_mock_verify_telegram_token,
        set_bot_webhook=_noop_set_webhook,
        delete_bot_webhook=_noop_delete_webhook,
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
def _alembic_for_lifecycle() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def lifecycle_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE_INTEGRATION)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    app.dependency_overrides[get_telegram_config_service] = _override_telegram_config_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_telegram_config_service, None)
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "lifecycle") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Lifecycle"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_create_web_initial_channel_is_active(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("web"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "Web Bot",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "web",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "active"
    assert body["primary_channel"] == "web"


def test_create_telegram_without_token_is_channel_pending(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("tg-pending"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "TG Pending Bot",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "channel_pending"
    assert body["primary_channel"] == "telegram"
    bot_id = body["id"]

    st = lifecycle_client.get(
        f"/api/v1/bots/{bot_id}/telegram/status",
        headers=_auth_headers(access),
    )
    assert st.status_code == 200, st.text
    assert st.json()["channel_status"] == "channel_pending"


def test_patch_active_blocked_until_telegram_connected(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("tg-block"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "TG Block Bot",
            "niche_id": "services",
            "goal_type": "sales",
            "initial_channel": "telegram",
        },
    )
    assert r.status_code == 201, r.text
    bot_id = r.json()["id"]

    patch = lifecycle_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(access),
        json={"status": "active"},
    )
    assert patch.status_code == 422, patch.text
    assert patch.json().get("code") == "bot_validation_error"


def test_create_telegram_with_valid_token_becomes_active(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("tg-ok"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "TG OK Bot",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
            "telegram_bot_token": API_TOKEN,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "active"
    assert body["primary_channel"] == "telegram"


def test_create_telegram_with_rejected_token_returns_telegram_error(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("tg-bad"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "TG Bad Bot",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
            "telegram_bot_token": "123456789:AAH___BAD___token_xx",
        },
    )
    assert r.status_code == 422, r.text
    assert r.json().get("code") == "telegram_token_invalid"
    # No 201 — wizard/API must not report a successful create for an invalid token.


def test_connect_telegram_promotes_channel_pending_bot_to_active(lifecycle_client: TestClient) -> None:
    access = _register_and_get_access(lifecycle_client, _unique_email("tg-promote"))
    r = lifecycle_client.post(
        "/api/v1/bots",
        headers=_auth_headers(access),
        json={
            "name": "TG Promote Bot",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
        },
    )
    assert r.status_code == 201, r.text
    bot_id = r.json()["id"]
    assert r.json()["status"] == "channel_pending"

    conn = lifecycle_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    assert conn.status_code == 200, conn.text

    get_b = lifecycle_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(access))
    assert get_b.status_code == 200, get_b.text
    assert get_b.json()["status"] == "active"
