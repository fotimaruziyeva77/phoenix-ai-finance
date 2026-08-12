"""
Multi-channel conversation unification (PostgreSQL + Alembic head).

Validates:
  * Widget session + Telegram thread services persist distinct ``Conversation.channel`` values.
  * ``get_active_conversation_for_channel`` / thin wrappers do not cross-resolve threads.
  * Optional E2E: public widget HTTP + Telegram webhook both exercise ``AIService.send_bot_message``
    (mocked for Telegram) and leave ``web_widget`` vs ``telegram`` rows in the database.
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
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.api.deps import get_telegram_config_service, get_telegram_webhook_inbound_service
from app.core.config import Settings, get_settings
from app.core.db import dispose_engine, get_db, get_session_maker
from app.integrations.telegram_bot_verify import TelegramBotVerificationResult, TelegramTokenVerificationError
from app.lib.chat_channels import (
    CONVERSATION_CHANNEL_TELEGRAM,
    CONVERSATION_CHANNEL_WEB_WIDGET,
)
from app.lib.integration_secrets_crypto import decrypt_integration_secret
from app.main import app
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai_chat import SendBotMessageResult
from app.services.conversation_thread_service import ConversationThreadService
from app.services.telegram_config_service import TelegramConfigService
from app.services.telegram_webhook_inbound_service import TelegramWebhookInboundService
from app.services.web_widget_session_service import WebWidgetSessionService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration_db import integration_database_url
from tests.public_widget_paths import public_widget_chat_path
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_MC = "m" * 32
API_TOKEN = "123456789:AAH_multi_channel_integration_token_xx"
PUBLIC_API_BASE = "https://api.mc-channel.test"


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


def _unique_email(prefix: str = "mc") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


class _FakeProviderOk(AIProvider):
    reply_text: str = "Widget visitor reply."

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-multi-channel-test"

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


async def _noop_set_webhook(_t: str, _u: str, _s: str) -> None:
    return None


async def _noop_delete_webhook(_t: str) -> None:
    return None


async def _mock_verify(token: str) -> TelegramBotVerificationResult:
    if "___BAD___" in token:
        raise TelegramTokenVerificationError("no")
    return TelegramBotVerificationResult(
        telegram_bot_id=99001,
        username="mc_unified_bot",
        first_name="MC",
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


def test_widget_and_telegram_threads_same_bot_distinct_channels_and_keys(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service-layer thread creation: one bot, two ingress keys, no column bleed."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        visitor_key = "uuuuuuuuuuuuuuuu"
        tg_chat_id = 88110022
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("owner"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Multi-channel Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bid, oid = bot.id, owner.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                wsvc = WebWidgetSessionService(chat, bots)
                tsvc = ConversationThreadService(chat)
                wconv, vk = await wsvc.get_or_create_conversation(
                    bot_id=bid,
                    visitor_session_key=visitor_key,
                )
                tconv = await tsvc.get_or_create_telegram_thread(
                    bot_id=bid,
                    owner_id=oid,
                    niche_id_snapshot="education",
                    telegram_chat_id=tg_chat_id,
                )
                assert vk == visitor_key
                assert wconv.id != tconv.id
                assert wconv.channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert wconv.public_visitor_session_key == visitor_key
                assert wconv.telegram_chat_id is None
                assert tconv.channel == CONVERSATION_CHANNEL_TELEGRAM
                assert tconv.telegram_chat_id == tg_chat_id
                assert tconv.public_visitor_session_key is None

                same_w = await chat.get_active_conversation_for_channel(
                    bot_id=bid,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    public_visitor_session_key=visitor_key,
                )
                same_t = await chat.get_active_conversation_for_channel(
                    bot_id=bid,
                    channel=CONVERSATION_CHANNEL_TELEGRAM,
                    telegram_chat_id=tg_chat_id,
                )
                assert same_w is not None and same_w.id == wconv.id
                assert same_t is not None and same_t.id == tconv.id

                assert (
                    await chat.get_active_web_widget_conversation(
                        bot_id=bid,
                        public_visitor_session_key=visitor_key,
                    )
                ).id == wconv.id
                assert (
                    await chat.get_active_telegram_conversation(
                        bot_id=bid,
                        telegram_chat_id=tg_chat_id,
                    )
                ).id == tconv.id

                no_cross = await chat.get_active_conversation_for_channel(
                    bot_id=bid,
                    channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                    public_visitor_session_key="zzzzzzzzzzzzzzzz",
                )
                assert no_cross is None

                await chat.commit()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_get_active_conversation_for_channel_does_not_cross_resolve_channels(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Telegram external id must not match a web_widget row; visitor key must not match telegram."""

    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        visitor_key = "vvvvvvvvvvvvvvvv"
        tg_chat_id = 33445566
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("iso"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="ISO Bot",
                    niche_id="retail",
                    goal_type="faq",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                bid, oid = bot.id, owner.id
                await session.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                bots = BotRepository(session)
                wsvc = WebWidgetSessionService(chat, bots)
                tsvc = ConversationThreadService(chat)
                await wsvc.get_or_create_conversation(bot_id=bid, visitor_session_key=visitor_key)
                await tsvc.get_or_create_telegram_thread(
                    bot_id=bid,
                    owner_id=oid,
                    niche_id_snapshot="retail",
                    telegram_chat_id=tg_chat_id,
                )
                await chat.commit()

            async with sm() as session:
                chat = AIChatRepository(session)
                assert (
                    await chat.get_active_conversation_for_channel(
                        bot_id=bid,
                        channel=CONVERSATION_CHANNEL_TELEGRAM,
                        telegram_chat_id=tg_chat_id,
                    )
                ).channel == CONVERSATION_CHANNEL_TELEGRAM
                assert (
                    await chat.get_active_conversation_for_channel(
                        bot_id=bid,
                        channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                        public_visitor_session_key=visitor_key,
                    )
                ).channel == CONVERSATION_CHANNEL_WEB_WIDGET
                assert (
                    await chat.get_active_conversation_for_channel(
                        bot_id=bid,
                        channel=CONVERSATION_CHANNEL_WEB_WIDGET,
                        public_visitor_session_key=str(tg_chat_id).ljust(16, "0")[:16],
                    )
                ) is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def _register(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "MC User"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_bot_support(client: TestClient, access: str, *, name: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth(access),
        json={"name": name, "niche_id": "education", "goal_type": "support"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _create_bot_sales(client: TestClient, access: str, *, name: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth(access),
        json={"name": name, "niche_id": "education", "goal_type": "sales"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _connect_telegram(client: TestClient, access: str, bot_id: str) -> None:
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


def test_widget_http_and_telegram_webhook_persist_distinct_channels_and_use_send_bot_message(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    E2E: public widget chat (real AIService + fake provider) and Telegram inbound (mocked AI)
    on one deployment; both should call ``send_bot_message`` and store correct ``channel``.
    """
    ai_calls: list[dict[str, Any]] = []

    async def _mock_send_text(*, bot_token: str, chat_id: int, text: str) -> None:
        del bot_token, chat_id, text

    async def _ai_side_effect(bot, owner, message_text: str, conversation_id=None):
        assert conversation_id is not None
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
            assistant_text="tg mock reply",
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
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_MC)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-mc-placeholder")
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE)
    get_settings.cache_clear()

    _patch_fake_provider(monkeypatch)

    asyncio.run(dispose_engine())
    app.dependency_overrides[get_telegram_config_service] = _override_telegram_config_service
    app.dependency_overrides[get_telegram_webhook_inbound_service] = _override_inbound

    try:
        with TestClient(app) as client:
            access = _register(client, _unique_email("e2e"))
            bot_w = _create_bot_support(client, access, name="Widget Side Bot")
            w = client.get(f"/api/v1/bots/{bot_w}/widget", headers=_auth(access))
            assert w.status_code == 200, w.text
            public_key = str(w.json()["public_widget_key"])

            rw = client.post(
                public_widget_chat_path(public_key),
                json={"message": "Hello widget unified test"},
            )
            assert rw.status_code == 200, rw.text
            w_cid = rw.json()["conversation_id"]

            bot_t = _create_bot_sales(client, access, name="Telegram Side Bot")
            _connect_telegram(client, access, bot_t)
            secret = _webhook_secret(bot_t)
            chat_id = 66006600

            rt = client.post(
                f"/api/v1/public/telegram/{bot_t}/webhook",
                headers={"X-Telegram-Bot-Api-Secret-Token": secret},
                content=_message_update(chat_id, "Hello telegram unified test"),
            )
            assert rt.status_code == 200, rt.text

        assert len(ai_calls) == 1
        assert ai_calls[0]["message"] == "Hello telegram unified test"
        t_cid = str(ai_calls[0]["conversation_id"])

        async def _load_channels() -> tuple[str | None, str | None]:
            sm = get_session_maker()
            async with sm() as session:
                w_row = (
                    await session.execute(
                        text("SELECT channel FROM conversations WHERE id = CAST(:id AS uuid)"),
                        {"id": w_cid},
                    )
                ).scalar_one()
                t_row = (
                    await session.execute(
                        text("SELECT channel FROM conversations WHERE id = CAST(:id AS uuid)"),
                        {"id": t_cid},
                    )
                ).scalar_one()
                return (
                    str(w_row) if w_row is not None else None,
                    str(t_row) if t_row is not None else None,
                )

        w_ch, t_ch = asyncio.run(_load_channels())
        assert w_ch == CONVERSATION_CHANNEL_WEB_WIDGET
        assert t_ch == CONVERSATION_CHANNEL_TELEGRAM

        async def _message_count(conv_id: str) -> int:
            sm = get_session_maker()
            async with sm() as session:
                n = (
                    await session.execute(
                        text(
                            "SELECT COUNT(*) FROM messages "
                            "WHERE conversation_id = CAST(:id AS uuid)",
                        ),
                        {"id": conv_id},
                    )
                ).scalar_one()
                return int(n)

        assert asyncio.run(_message_count(w_cid)) >= 2
    finally:
        app.dependency_overrides.pop(get_telegram_config_service, None)
        app.dependency_overrides.pop(get_telegram_webhook_inbound_service, None)
        asyncio.run(dispose_engine())
        get_settings.cache_clear()
