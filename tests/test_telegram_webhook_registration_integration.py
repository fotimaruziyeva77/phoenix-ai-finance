"""
Telegram webhook registration flow (PostgreSQL + mocked Telegram setWebhook/deleteWebhook).

Mocks stand in for ``app.integrations.telegram_webhook_registration`` HTTP calls while the
service exercises real persistence and state transitions.

Checklist:
  1. Valid connect triggers webhook registration — ``test_connect_triggers_webhook_registration_mock``
  2. Disconnect removes webhook (mock) then DB row — ``test_disconnect_invokes_delete_webhook_then_removes_row``;
     delete failure keeps row — ``test_disconnect_failure_leaves_row_and_raises_clear_error``
  3. Webhook URL persists — ``test_webhook_url_persists_in_database``
  4. Registration failure maps to ``TelegramWebhookRegistrationError`` —
     ``test_registration_failure_raises_clean_error_and_leaves_disconnected_state``
  5. No broken inconsistent state / retry — ``test_registration_failure...`` + ``test_retry_after_registration_failure_connects_successfully``

Requires ``TEST_DATABASE_URL`` or host-reachable ``DATABASE_URL`` (see ``tests/integration_db.py``).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_verify import TelegramBotVerificationResult
from app.integrations.telegram_webhook_urls import build_telegram_webhook_url
from app.lib.integration_secrets_crypto import decrypt_integration_secret
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.services.telegram_config_exceptions import (
    TelegramWebhookClearError,
    TelegramWebhookRegistrationError,
)
from app.services.telegram_config_service import TelegramConfigService
from sqlalchemy import text

from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLAIN_TOKEN = "123456789:AAH_webhook_registration_integration_xxx"
JWT_TEST_KEY = "w" * 32
PUBLIC_API_BASE_TEST = "https://hooks.test.example"

VerifyTokenCallable = Callable[..., Awaitable[TelegramBotVerificationResult]]


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
def _alembic_for_webhook_registration_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "tg-wh") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _run_async_db(live_db_url: str, monkeypatch: pytest.MonkeyPatch, coro) -> None:
    async def runner() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        monkeypatch.setenv("JWT_SECRET_KEY", JWT_TEST_KEY)
        monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
        monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", PUBLIC_API_BASE_TEST)
        get_settings.cache_clear()
        try:
            await coro
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(runner())


async def _create_user(*, email: str) -> User:
    sm = get_session_maker()
    async with sm() as session:
        user = User(
            email=email,
            password_hash="bcrypt$dummy",
            role=UserRole.customer_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _delete_user_cascade(*, user_id: uuid.UUID) -> None:
    sm = get_session_maker()
    async with sm() as session:
        user = await session.get(User, user_id)
        if user is not None:
            await session.delete(user)
            await session.commit()


def _verify_ok(username: str = "wh_bot") -> VerifyTokenCallable:
    async def _verify(_token: str) -> TelegramBotVerificationResult:
        return TelegramBotVerificationResult(
            telegram_bot_id=900001,
            username=username,
            first_name="WH",
        )

    return _verify


async def _noop_set_webhook(_t: str, _u: str, _s: str) -> None:
    return None


async def _noop_delete_webhook(_t: str) -> None:
    return None


def test_connect_triggers_webhook_registration_mock(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid connect calls the webhook registrar once with token, canonical URL, and secret."""
    owner_email = _unique_email("reg")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            webhook_calls: list[tuple[str, str, str]] = []

            async def _record_set(token: str, url: str, secret: str) -> None:
                webhook_calls.append((token, url, secret))

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH Reg Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            expected_url = build_telegram_webhook_url(PUBLIC_API_BASE_TEST, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_record_set,
                    delete_bot_webhook=_noop_delete_webhook,
                )
                read = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            assert read.is_connected is True
            assert read.webhook_url == expected_url
            assert len(webhook_calls) == 1
            tok, u, sec = webhook_calls[0]
            assert tok == PLAIN_TOKEN
            assert u == expected_url
            assert len(sec) == 64
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_webhook_url_persists_in_database(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("url")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH URL Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            expected = build_telegram_webhook_url(PUBLIC_API_BASE_TEST, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_noop_set_webhook,
                )
                await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                row_url = (
                    await session.execute(
                        text("SELECT webhook_url FROM telegram_configs WHERE bot_id = CAST(:b AS uuid)"),
                        {"b": str(bot.id)},
                    )
                ).scalar_one()
                assert row_url == expected
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_disconnect_invokes_delete_webhook_then_removes_row(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("disc")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            delete_calls: list[str] = []

            async def _record_delete(token: str) -> None:
                delete_calls.append(token)

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH Disc Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_noop_set_webhook,
                    delete_bot_webhook=_record_delete,
                )
                await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            assert delete_calls == []

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    delete_bot_webhook=_record_delete,
                )
                await svc.disconnect_telegram_for_bot(owner, bot.id)

            assert len(delete_calls) == 1
            assert delete_calls[0] == PLAIN_TOKEN

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:b AS uuid)"),
                        {"b": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 0
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_registration_failure_raises_clean_error_and_leaves_disconnected_state(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("fail")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            async def _boom(_t: str, _u: str, _s: str) -> None:
                raise TelegramBotApiError(
                    TelegramApiErrorKind.WEBHOOK,
                    "Telegram webhook request failed.",
                )

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH Fail Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_boom,
                )
                with pytest.raises(TelegramWebhookRegistrationError):
                    await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                st = (
                    await session.execute(
                        text(
                            "SELECT is_connected, webhook_url, webhook_secret_token_encrypted "
                            "FROM telegram_configs WHERE bot_id = CAST(:b AS uuid)",
                        ),
                        {"b": str(bot.id)},
                    )
                ).one()
                assert st[0] is False
                assert st[1] is not None
                assert str(bot.id) in st[1]
                assert st[2] is not None
                enc_tok = (
                    await session.execute(
                        text("SELECT bot_token_encrypted FROM telegram_configs WHERE bot_id = CAST(:b AS uuid)"),
                        {"b": str(bot.id)},
                    )
                ).scalar_one()
                assert decrypt_integration_secret(enc_tok, settings) == PLAIN_TOKEN
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_retry_after_registration_failure_connects_successfully(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("retry")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            attempts = {"n": 0}

            async def _flaky_set(_token: str, _url: str, _secret: str) -> None:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise TelegramBotApiError(
                        TelegramApiErrorKind.TRANSPORT,
                        "Could not reach Telegram.",
                    )

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH Retry Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_flaky_set,
                )
                with pytest.raises(TelegramWebhookRegistrationError):
                    await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_flaky_set,
                )
                read = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            assert attempts["n"] == 2
            assert read.is_connected is True
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_disconnect_failure_leaves_row_and_raises_clear_error(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("del-fail")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            async def _boom_delete(_token: str) -> None:
                raise TelegramBotApiError(
                    TelegramApiErrorKind.TRANSPORT,
                    "Could not reach Telegram.",
                )

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH DelFail Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_noop_set_webhook,
                    delete_bot_webhook=_boom_delete,
                )
                await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    delete_bot_webhook=_boom_delete,
                )
                with pytest.raises(TelegramWebhookClearError):
                    await svc.disconnect_telegram_for_bot(owner, bot.id)

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:b AS uuid)"),
                        {"b": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 1
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_delete_webhook_mock_fixed_disconnect_succeeds_after_clear_failure(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After deleteWebhook fails, a retry with a succeeding mock completes disconnect."""
    owner_email = _unique_email("del-retry")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH DelRetry Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(
                    session,
                    repo,
                    settings,
                    verify_token=_verify_ok(),
                    set_bot_webhook=_noop_set_webhook,
                )
                await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async def _boom(_t: str) -> None:
                raise TelegramBotApiError(TelegramApiErrorKind.WEBHOOK, "x")

            deletes: list[str] = []

            async def _ok_delete(token: str) -> None:
                deletes.append(token)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(session, repo, settings, delete_bot_webhook=_boom)
                with pytest.raises(TelegramWebhookClearError):
                    await svc.disconnect_telegram_for_bot(owner, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = TelegramConfigService(session, repo, settings, delete_bot_webhook=_ok_delete)
                await svc.disconnect_telegram_for_bot(owner, bot.id)

            assert len(deletes) == 1
            assert deletes[0] == PLAIN_TOKEN
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())
