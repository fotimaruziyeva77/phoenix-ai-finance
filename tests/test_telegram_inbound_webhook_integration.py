"""
Telegram inbound webhook integration (PostgreSQL + mocked AIService + mocked outbound Telegram).

Checklist:
  1. Valid update → HTTP 200
  2. Conversation created on first message, same ``conversation_id`` on second (resume)
  3. ``AIService.send_bot_message`` invoked (integration point to sales / non-sales AI stack)
  4. Outbound send captured (mock replaces real ``sendMessage`` HTTP)
  5. ``conversations.channel`` = ``telegram`` and ``telegram_chat_id`` set
  6. Malformed JSON / empty message → 200, no AI call
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic import command
from alembic.config import Config
from app.api.deps import get_telegram_config_service, get_telegram_webhook_inbound_service
from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_db, get_session_maker
from app.integrations.telegram_bot_verify import TelegramBotVerificationResult, TelegramTokenVerificationError
from app.lib.chat_channels import CONVERSATION_CHANNEL_TELEGRAM
from app.lib.integration_secrets_crypto import decrypt_integration_secret
from app.main import app
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai_chat import SendBotMessageResult
from app.services.telegram_config_service import TelegramConfigService
from app.services.telegram_webhook_inbound_service import TelegramWebhookInboundService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "y" * 32
API_TOKEN = "123456789:AAH_tg_inbound_integration_test_token_xx"
PUBLIC_API_BASE = "https://api.tg-inbound.test"


async def _noop_set_webhook(_t: str, _u: str, _s: str) -> None:
    return None


async def _noop_delete_webhook(_t: str) -> None:
    return None


async def _mock_verify(token: str) -> TelegramBotVerificationResult:
    if "___BAD___" in token:
        raise TelegramTokenVerificationError("no")
    return TelegramBotVerificationResult(
        telegram_bot_id=88001,
        username="inbound_test_bot",
        first_name="Inbound",
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
        verify_token=_mock_verify,
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
def _alembic_head() -> None:
    u = _integration_db_url()
    assert u is not None
    _alembic_upgrade_head(u)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def inbound_integration_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str):
    """TestClient with Telegram connect mocks + captured AI / outbound sends."""
    ai_calls: list[dict[str, Any]] = []
    send_calls: list[dict[str, Any]] = []

    async def _mock_send_text(*, bot_token: str, chat_id: int, text: str) -> None:
        send_calls.append({"bot_token_tail": bot_token[-8:], "chat_id": chat_id, "text": text})

    async def _ai_side_effect(bot, owner, message_text: str, conversation_id=None):
        assert conversation_id is not None
        assert bot.goal_type == "sales"
        ai_calls.append(
            {
                "bot_id": bot.id,
                "owner_id": owner.id,
                "message": message_text,
                "conversation_id": conversation_id,
            },
        )
        return SendBotMessageResult(
            conversation_id=conversation_id,
            user_message_id=uuid.uuid4(),
            assistant_message_id=uuid.uuid4(),
            assistant_text="Mock assistant from sales-stack gateway",
            model_name="mock",
            success=True,
        )

    def _override_inbound(
        session: AsyncSession = Depends(get_db),
        settings: Settings = Depends(_settings_for_dep),
    ) -> TelegramWebhookInboundService:
        chat_repo = AIChatRepository(session)
        mock_ai = MagicMock()
        mock_ai.send_bot_message = AsyncMock(side_effect=_ai_side_effect)
        return TelegramWebhookInboundService(
            chat_repo,
            UserRepository(session),
            mock_ai,
            settings,
            send_telegram_text=_mock_send_text,
        )

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    app.dependency_overrides[get_telegram_config_service] = _override_telegram_config_service
    app.dependency_overrides[get_telegram_webhook_inbound_service] = _override_inbound
    with TestClient(app) as client:
        yield client, {"ai": ai_calls, "send": send_calls}
    app.dependency_overrides.pop(get_telegram_config_service, None)
    app.dependency_overrides.pop(get_telegram_webhook_inbound_service, None)
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "tg-in") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "TG Inbound"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_bot_sales(client: TestClient, access: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth(access),
        json={"name": "Inbound Sales Bot", "niche_id": "education", "goal_type": "sales"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _connect(client: TestClient, access: str, bot_id: str) -> None:
    r = client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=_auth(access),
        json={"bot_token": API_TOKEN},
    )
    assert r.status_code == 200, r.text


def _webhook_secret(bot_id: str) -> str:
    async def _load() -> str:
        sm = get_session_maker()
        async with sm() as session:
            enc = (
                await session.execute(
                    text(
                        "SELECT webhook_secret_token_encrypted FROM telegram_configs "
                        "WHERE bot_id = CAST(:b AS uuid)",
                    ),
                    {"b": bot_id},
                )
            ).scalar_one()
            return decrypt_integration_secret(enc, get_settings())

    return asyncio.run(_load())


def _message_update(chat_id: int, text_msg: str, update_id: int = 1) -> bytes:
    return json.dumps(
        {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "chat": {"id": chat_id, "type": "private"},
                "text": text_msg,
            },
        },
    ).encode()


def test_inbound_valid_update_invokes_ai_and_sends_reply(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v1"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)
    chat_id = 42424242

    r = client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=_message_update(chat_id, "Hello Telegram"),
    )
    assert r.status_code == 200, r.text
    assert len(calls["ai"]) == 1
    assert calls["ai"][0]["message"] == "Hello Telegram"
    assert len(calls["send"]) == 1
    assert calls["send"][0]["chat_id"] == chat_id
    assert calls["send"][0]["text"] == "Mock assistant from sales-stack gateway"


def test_inbound_resumes_same_conversation(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v2"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)
    chat_id = 9000001

    for i, msg in enumerate(("First", "Second"), start=1):
        r = client.post(
            f"/api/v1/public/telegram/{bot_id}/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": secret},
            content=_message_update(chat_id, msg, update_id=i),
        )
        assert r.status_code == 200, r.text

    assert len(calls["ai"]) == 2
    assert calls["ai"][0]["conversation_id"] == calls["ai"][1]["conversation_id"]


def test_inbound_stores_channel_telegram(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v3"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)
    chat_id = 777001

    client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=_message_update(chat_id, "channel check"),
    )
    conv_id = calls["ai"][0]["conversation_id"]

    async def _check() -> tuple[str | None, int | None]:
        sm = get_session_maker()
        async with sm() as session:
            row = (
                await session.execute(
                    text(
                        "SELECT channel, telegram_chat_id FROM conversations "
                        "WHERE id = CAST(:id AS uuid)",
                    ),
                    {"id": str(conv_id)},
                )
            ).one()
            return str(row[0]) if row[0] is not None else None, int(row[1]) if row[1] is not None else None

    ch, tid = asyncio.run(_check())
    assert ch == CONVERSATION_CHANNEL_TELEGRAM
    assert tid == chat_id


def test_inbound_malformed_json_no_ai(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v4"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)

    r = client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=b"{not-json",
    )
    assert r.status_code == 200
    assert calls["ai"] == []
    assert calls["send"] == []


def test_inbound_parse_safe_no_text_no_ai(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v5"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)

    r = client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=json.dumps({"update_id": 1, "message": {"message_id": 1, "chat": {"id": 1}}}).encode(),
    )
    assert r.status_code == 200
    assert calls["ai"] == []
    assert calls["send"] == []


def test_inbound_invalid_update_id_no_ai(inbound_integration_client) -> None:
    client, calls = inbound_integration_client
    access = _register(client, _unique_email("v6"))
    bot_id = _create_bot_sales(client, access)
    _connect(client, access, bot_id)
    secret = _webhook_secret(bot_id)

    r = client.post(
        f"/api/v1/public/telegram/{bot_id}/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        content=json.dumps({"update_id": "bad", "message": {"text": "x", "chat": {"id": 1}}}).encode(),
    )
    assert r.status_code == 200
    assert calls["ai"] == []
    assert calls["send"] == []
