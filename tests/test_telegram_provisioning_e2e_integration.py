"""
Telegram provisioning E2E integration (real ``TelegramConfigService``, real DB, sandboxed Telegram HTTP).

Unlike ``test_bot_telegram_api_integration.py``, this module does **not** override
``get_telegram_config_service``. Outbound Telegram is replaced only via
``tests.fixtures.telegram_provisioning_harness.install_telegram_outer_boundary_sandbox``.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.lib.telegram_token_crypto import decrypt_telegram_bot_token
from app.main import app
from fastapi.testclient import TestClient

from tests.fixtures.telegram_provisioning_harness import (
    TelegramOuterBoundarySandbox,
    fetch_telegram_config_row_for_bot,
    install_telegram_outer_boundary_sandbox,
)
from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32
PUBLIC_API_BASE_INTEGRATION = "https://api.integration.test"

TOKEN_OK = "1234567890:AAH_e2e_tg_provision_ok_token_xx"
TOKEN_ROTATE = "1234567890:AAH_e2e_tg_provision_rotate_tok_xx"
TOKEN_REJECT = "1234567890:AAH___TG_BAD___e2e_reject_token_xx"


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.telegram_provisioning_e2e,
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
def _alembic_for_telegram_provision_e2e() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def tg_outer_sandbox(monkeypatch: pytest.MonkeyPatch) -> TelegramOuterBoundarySandbox:
    sandbox = TelegramOuterBoundarySandbox()
    sandbox.telegram_bot_id = uuid.uuid4().int % 900_000_000 + 100_000_000
    sandbox.reject_token_substring = "___TG_BAD___"
    install_telegram_outer_boundary_sandbox(monkeypatch, sandbox)
    return sandbox


@pytest.fixture
def telegram_provision_e2e_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE_INTEGRATION)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "tg-e2e") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "TG E2E"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str) -> uuid.UUID:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={"name": "TG E2E Bot", "niche_id": "education", "goal_type": "support"},
    )
    assert r.status_code == 201, r.text
    return uuid.UUID(str(r.json()["id"]))


def _row_decrypt_token(row) -> str:
    settings = get_settings()
    enc = row["bot_token_encrypted"]
    assert enc
    return decrypt_telegram_bot_token(str(enc), settings)


def test_e2e_validate_hits_verify_only_no_webhook_no_persisted_token(
    telegram_provision_e2e_client: TestClient,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("val"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/token/validate",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valid"] is True
    assert body["telegram_bot_id"] == tg_outer_sandbox.telegram_bot_id
    assert tg_outer_sandbox.verify_calls == [TOKEN_OK]
    assert tg_outer_sandbox.set_webhook_calls == []

    row = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row is None


def test_e2e_start_provisioning_validate_leaves_token_null(
    telegram_provision_e2e_client: TestClient,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("pend"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    s0 = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/provisioning/start",
        headers=_auth_headers(access),
    )
    assert s0.status_code == 200, s0.text
    assert s0.json()["channel_status"] == "channel_pending"

    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/token/validate",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    assert r.status_code == 200, r.text
    assert tg_outer_sandbox.set_webhook_calls == []

    row = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row is not None
    assert row["provisioning_status"] == "channel_pending"
    assert row["bot_token_encrypted"] in (None, "")


def test_e2e_connect_encrypts_persists_webhook_then_active_status(
    telegram_provision_e2e_client: TestClient,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("conn"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["channel_status"] == "active"
    assert data["connected"] is True
    assert data["configured"] is True

    assert len(tg_outer_sandbox.set_webhook_calls) == 1
    _token, url, secret = tg_outer_sandbox.set_webhook_calls[0]
    assert _token == TOKEN_OK
    assert url.startswith(PUBLIC_API_BASE_INTEGRATION)
    assert str(bot_id) in url
    assert url.endswith("/webhook")
    assert len(secret) == 64

    row = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row is not None
    assert row["provisioning_status"] == "active"
    assert row["is_connected"] is True
    enc = row["bot_token_encrypted"]
    assert enc
    assert TOKEN_OK not in str(enc)
    plain = _row_decrypt_token(row)
    assert plain == TOKEN_OK
    meta = row["metadata_json"] or {}
    assert meta.get("telegram_bot_id") == tg_outer_sandbox.telegram_bot_id

    st = telegram_provision_e2e_client.get(
        f"/api/v1/bots/{bot_id}/telegram/status",
        headers=_auth_headers(access),
    )
    assert st.status_code == 200, st.text
    assert st.json()["channel_status"] == "active"


def test_e2e_webhook_failure_keeps_pending_until_retry_connect(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE_INTEGRATION)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    tg_outer_sandbox.force_set_webhook_failure = True

    with TestClient(app) as client:
        access = _register_and_get_access(client, _unique_email("wh-fail"))
        bot_id = _create_bot(client, access)
        r = client.post(
            f"/api/v1/bots/{bot_id}/telegram/connect",
            headers=_auth_headers(access),
            json={"bot_token": TOKEN_OK},
        )
        assert r.status_code == 502, r.text

    row = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row is not None
    assert row["provisioning_status"] == "channel_pending"
    assert row["is_connected"] is False
    assert row["bot_token_encrypted"]
    plain = _row_decrypt_token(row)
    assert plain == TOKEN_OK
    assert len(tg_outer_sandbox.set_webhook_calls) == 1

    tg_outer_sandbox.force_set_webhook_failure = False
    asyncio.run(dispose_engine())
    get_settings.cache_clear()
    with TestClient(app) as client:
        r2 = client.post(
            f"/api/v1/bots/{bot_id}/telegram/connect",
            headers=_auth_headers(access),
            json={"bot_token": TOKEN_OK},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["channel_status"] == "active"

    row2 = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row2 is not None
    assert row2["provisioning_status"] == "active"
    assert row2["is_connected"] is True
    assert len(tg_outer_sandbox.set_webhook_calls) == 2

    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def test_e2e_invalid_token_failed_validation_persisted(
    telegram_provision_e2e_client: TestClient,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("bad"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_REJECT},
    )
    assert r.status_code == 422, r.text

    row = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row is not None
    assert row["provisioning_status"] == "failed_validation"
    assert row["is_connected"] is False
    assert row["bot_token_encrypted"] in (None, "")
    assert tg_outer_sandbox.set_webhook_calls == []


def test_e2e_short_token_422(telegram_provision_e2e_client: TestClient) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("short"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": "short"},
    )
    assert r.status_code == 422, r.text


def test_e2e_missing_bot_token_field_422(
    telegram_provision_e2e_client: TestClient,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("miss"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={},
    )
    assert r.status_code == 422, r.text


def test_e2e_webhook_sync_second_setwebhook_idempotent_recovery(
    telegram_provision_e2e_client: TestClient,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("sync"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    assert len(tg_outer_sandbox.set_webhook_calls) == 1

    r = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/webhook/sync",
        headers=_auth_headers(access),
    )
    assert r.status_code == 200, r.text
    assert r.json()["channel_status"] == "active"
    assert len(tg_outer_sandbox.set_webhook_calls) == 2
    assert tg_outer_sandbox.set_webhook_calls[0][1] == tg_outer_sandbox.set_webhook_calls[1][1]


def test_e2e_repeated_connect_rotates_ciphertext_and_webhook(
    telegram_provision_e2e_client: TestClient,
    live_db_url: str,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("rot"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    row1 = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row1 is not None
    ct1 = str(row1["bot_token_encrypted"])

    telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_ROTATE},
    )
    row2 = asyncio.run(fetch_telegram_config_row_for_bot(live_db_url, bot_id))
    assert row2 is not None
    ct2 = str(row2["bot_token_encrypted"])
    assert ct2 != ct1
    assert _row_decrypt_token(row2) == TOKEN_ROTATE
    assert len(tg_outer_sandbox.set_webhook_calls) == 2
    assert tg_outer_sandbox.set_webhook_calls[-1][0] == TOKEN_ROTATE


def test_e2e_disconnect_invokes_delete_webhook(
    telegram_provision_e2e_client: TestClient,
    tg_outer_sandbox: TelegramOuterBoundarySandbox,
) -> None:
    access = _register_and_get_access(telegram_provision_e2e_client, _unique_email("disc"))
    bot_id = _create_bot(telegram_provision_e2e_client, access)
    telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth_headers(access),
        json={"bot_token": TOKEN_OK},
    )
    d = telegram_provision_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/disconnect",
        headers=_auth_headers(access),
    )
    assert d.status_code == 204, d.text
    assert tg_outer_sandbox.delete_webhook_calls == [TOKEN_OK]
