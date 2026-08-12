"""
Owner Telegram API integration tests (auth, owner scoping, mocked Telegram verify).

Checklist:
  1. Owner can connect with a valid token (mocked Telegram OK).
  2. Owner can fetch Telegram status (before/after connect).
  3. Owner can disconnect (204) and status clears.
  4. Invalid token → clean API error (no Telegram/raw token leakage).
  5. Non-owner cannot connect / read status / disconnect another user's bot.
  6. Connect + status JSON never contains the secret token or ciphertext hints.
  7. Token validate, webhook sync success/failure, duplicate bot, repeated connect (HTTP).
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
from app.api.deps import get_telegram_config_service
from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_db, get_session_maker
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_verify import (
    TelegramBotVerificationResult,
    TelegramTokenVerificationError,
)
from app.lib.integration_secrets_crypto import decrypt_integration_secret
from app.main import app
from app.repositories.bot_repository import BotRepository
from app.services.telegram_config_service import TelegramConfigService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32

API_TOKEN = "123456789:AAH_bot_telegram_api_integration_test_xxx"
API_TOKEN_ROTATE = "123456789:AAH_bot_telegram_api_integration_rotate_xx"
# Long enough for schema; mock verify treats this as Telegram-invalid.
REJECTED_BY_MOCK_TOKEN = "987654321:AAH___TG_REJECT___integration_bad_token_xx"
PUBLIC_API_BASE_INTEGRATION = "https://api.integration.test"


async def _noop_set_webhook(_token: str, url: str, _secret: str) -> None:
    assert url.startswith(PUBLIC_API_BASE_INTEGRATION)
    assert "/api/v1/public/telegram/" in url
    assert url.endswith("/webhook")
    assert len(_secret) == 64


async def _noop_delete_webhook(_token: str) -> None:
    assert len(_token) >= 10


async def _mock_verify_telegram_token(token: str) -> TelegramBotVerificationResult:
    assert len(token) >= 10
    if "___TG_REJECT___" in token:
        raise TelegramTokenVerificationError("internal detail must not reach client")
    return TelegramBotVerificationResult(
        telegram_bot_id=777001,
        username="api_integration_bot",
        first_name="API",
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


def _override_telegram_webhook_fails_on_second_set():
    calls: list[int] = [0]

    async def _set_wh(token: str, url: str, secret: str) -> None:
        calls[0] += 1
        if calls[0] >= 2:
            raise TelegramBotApiError(TelegramApiErrorKind.WEBHOOK, "webhook sync failed")
        await _noop_set_webhook(token, url, secret)

    def _override(
        session: AsyncSession = Depends(get_db),
        settings: Settings = Depends(_settings_for_dep),
    ) -> TelegramConfigService:
        return TelegramConfigService(
            session,
            BotRepository(session),
            settings,
            verify_token=_mock_verify_telegram_token,
            set_bot_webhook=_set_wh,
            delete_bot_webhook=_noop_delete_webhook,
        )

    return _override


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
def _alembic_for_bot_telegram_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def telegram_api_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
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


@pytest.fixture
def telegram_api_client_webhook_second_call_fails(
    monkeypatch: pytest.MonkeyPatch, live_db_url: str
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE_INTEGRATION)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    app.dependency_overrides[get_telegram_config_service] = _override_telegram_webhook_fails_on_second_set()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_telegram_config_service, None)
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "tg-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "TG API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={"name": "TG API Bot", "niche_id": "education", "goal_type": "support"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _tg_connect_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/connect"


def _tg_status_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/status"


def _tg_disconnect_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/disconnect"


def _tg_validate_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/token/validate"


def _tg_sync_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/webhook/sync"


def test_connect_returns_status_without_token(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("conn"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["channel_status"] == "active"
    assert data["configured"] is True
    assert data["connected"] is True
    assert data["bot_username"] == "api_integration_bot"
    assert data["last_verified_at"] is not None
    assert data["webhook_url_configured"] is True
    blob = r.text
    assert API_TOKEN not in blob
    assert "AAH_bot_telegram" not in blob


def test_status_reflects_connection(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("stat"))
    bot_id = _create_bot(telegram_api_client, access)
    r0 = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert r0.status_code == 200
    assert r0.json()["channel_status"] == "draft"
    assert r0.json()["configured"] is False
    assert r0.json()["connected"] is False

    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    r1 = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert r1.status_code == 200
    assert r1.json()["channel_status"] == "active"
    assert r1.json()["configured"] is True
    assert r1.json()["connected"] is True
    assert r1.json()["bot_username"] == "api_integration_bot"


def test_disconnect_then_status_clear(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("disc"))
    bot_id = _create_bot(telegram_api_client, access)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    d = telegram_api_client.post(_tg_disconnect_url(bot_id), headers=_auth_headers(access))
    assert d.status_code == 204, d.text

    r = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert r.status_code == 200
    assert r.json()["channel_status"] == "draft"
    assert r.json()["configured"] is False


def test_connect_requires_auth(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("auth"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(_tg_connect_url(bot_id), json={"bot_token": API_TOKEN})
    assert r.status_code == 401


def test_connect_short_token_validation(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("val"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": "short"},
    )
    assert r.status_code == 422


def test_connect_invalid_token_telegram_clean_error_no_leak(
    telegram_api_client: TestClient,
) -> None:
    """Token passes length validation but mocked Telegram verification fails."""
    access = _register_and_get_access(telegram_api_client, _unique_email("inv"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": REJECTED_BY_MOCK_TOKEN},
    )
    assert r.status_code == 422, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "telegram_token_invalid"
    low = r.text.lower()
    assert "internal detail" not in low
    assert "___tg_reject___" not in low
    assert REJECTED_BY_MOCK_TOKEN not in r.text

    rs = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert rs.status_code == 200
    body = rs.json()
    assert body["channel_status"] == "failed_validation"
    assert body["configured"] is False
    assert body["connected"] is False
    assert body.get("last_error_code") == "telegram_token_invalid"


def _tg_provision_start_url(bot_id: str) -> str:
    return f"/api/v1/bots/{bot_id}/telegram/provisioning/start"


def test_provisioning_start_returns_channel_pending(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("prov"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(
        _tg_provision_start_url(bot_id),
        headers=_auth_headers(access),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["channel_status"] == "channel_pending"
    assert data["configured"] is False
    assert data["connected"] is False


def test_non_owner_cannot_connect(telegram_api_client: TestClient) -> None:
    a = _register_and_get_access(telegram_api_client, _unique_email("own-a"))
    b = _register_and_get_access(telegram_api_client, _unique_email("own-b"))
    bot_id = _create_bot(telegram_api_client, a)
    r = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(b),
        json={"bot_token": API_TOKEN},
    )
    assert r.status_code == 403


def test_non_owner_cannot_read_status(telegram_api_client: TestClient) -> None:
    a = _register_and_get_access(telegram_api_client, _unique_email("st-a"))
    b = _register_and_get_access(telegram_api_client, _unique_email("st-b"))
    bot_id = _create_bot(telegram_api_client, a)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(a),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(b))
    assert r.status_code == 403


def test_non_owner_cannot_disconnect(telegram_api_client: TestClient) -> None:
    a = _register_and_get_access(telegram_api_client, _unique_email("ndo-a"))
    b = _register_and_get_access(telegram_api_client, _unique_email("ndo-b"))
    bot_id = _create_bot(telegram_api_client, a)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(a),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client.post(_tg_disconnect_url(bot_id), headers=_auth_headers(b))
    assert r.status_code == 403


def test_no_sensitive_substrings_in_connect_and_status_responses(
    telegram_api_client: TestClient,
) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("leak"))
    bot_id = _create_bot(telegram_api_client, access)
    forbidden = (
        API_TOKEN,
        "AAH_bot_telegram",
        "bot_token",
        "bot_token_encrypted",
        "gAAAA",  # Fernet ciphertext prefix
    )
    r0 = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert r0.status_code == 200
    for s in forbidden:
        assert s not in r0.text

    r1 = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    assert r1.status_code == 200
    for s in forbidden:
        assert s not in r1.text

    r2 = telegram_api_client.get(_tg_status_url(bot_id), headers=_auth_headers(access))
    assert r2.status_code == 200
    for s in forbidden:
        assert s not in r2.text


def test_disconnect_idempotent_not_found(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("idemp"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(_tg_disconnect_url(bot_id), headers=_auth_headers(access))
    assert r.status_code == 404
    assert r.json().get("error", {}).get("code") == "telegram_config_not_found"


def test_public_telegram_webhook_accepts_valid_secret(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("wh"))
    bot_id = _create_bot(telegram_api_client, access)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )

    async def _load_secret() -> str:
        sm = get_session_maker()
        async with sm() as session:
            enc = (
                await session.execute(
                    text(
                        "SELECT webhook_secret_token_encrypted FROM telegram_configs "
                        "WHERE bot_id = CAST(:bid AS uuid)",
                    ),
                    {"bid": bot_id},
                )
            ).scalar_one()
            return decrypt_integration_secret(enc, get_settings())

    secret = asyncio.run(_load_secret())
    r = telegram_api_client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=json.dumps({"update_id": 1}).encode(),
    )
    assert r.status_code == 200, r.text


def test_public_telegram_webhook_rejects_missing_secret(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("wh2"))
    bot_id = _create_bot(telegram_api_client, access)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        content=json.dumps({"update_id": 1}).encode(),
    )
    assert r.status_code == 404


def test_validate_token_returns_public_ids(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("val-ok"))
    bot_id = _create_bot(telegram_api_client, access)
    r = telegram_api_client.post(
        _tg_validate_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["valid"] is True
    assert data["telegram_bot_id"] == 777001
    assert data["bot_username"] == "api_integration_bot"
    assert API_TOKEN not in r.text


def test_validate_token_duplicate_telegram_bot_returns_409(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("dup-val"))
    bot_a = _create_bot(telegram_api_client, access)
    bot_b = _create_bot(telegram_api_client, access)
    telegram_api_client.post(
        _tg_connect_url(bot_a),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client.post(
        _tg_validate_url(bot_b),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN_ROTATE},
    )
    assert r.status_code == 409, r.text
    assert r.json().get("error", {}).get("code") == "telegram_bot_already_attached"


def test_webhook_sync_keeps_active(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("sync-ok"))
    bot_id = _create_bot(telegram_api_client, access)
    telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client.post(
        _tg_sync_url(bot_id),
        headers=_auth_headers(access),
    )
    assert r.status_code == 200, r.text
    assert r.json()["channel_status"] == "active"
    assert r.json()["connected"] is True


def test_webhook_sync_failure_after_successful_connect(
    telegram_api_client_webhook_second_call_fails: TestClient,
) -> None:
    access = _register_and_get_access(telegram_api_client_webhook_second_call_fails, _unique_email("sync-fail"))
    bot_id = _create_bot(telegram_api_client_webhook_second_call_fails, access)
    telegram_api_client_webhook_second_call_fails.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    r = telegram_api_client_webhook_second_call_fails.post(
        _tg_sync_url(bot_id),
        headers=_auth_headers(access),
    )
    assert r.status_code == 502, r.text
    assert r.json().get("error", {}).get("code") == "telegram_webhook_registration_failed"

    rs = telegram_api_client_webhook_second_call_fails.get(
        _tg_status_url(bot_id),
        headers=_auth_headers(access),
    )
    assert rs.status_code == 200
    body = rs.json()
    assert body["channel_status"] == "channel_pending"
    assert body["configured"] is True
    assert body["connected"] is False
    assert body.get("last_error_code") == "telegram_webhook_registration_failed"


def test_repeated_connect_same_bot_remains_active(telegram_api_client: TestClient) -> None:
    access = _register_and_get_access(telegram_api_client, _unique_email("reconn-api"))
    bot_id = _create_bot(telegram_api_client, access)
    r1 = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN},
    )
    assert r1.status_code == 200
    r2 = telegram_api_client.post(
        _tg_connect_url(bot_id),
        headers=_auth_headers(access),
        json={"bot_token": API_TOKEN_ROTATE},
    )
    assert r2.status_code == 200, r.text
    assert r2.json()["channel_status"] == "active"
    assert r2.json()["configured"] is True
