"""
TelegramConfigService integration tests (PostgreSQL + mocked Telegram verification).

Covers encryption at rest, connect/disconnect lifecycle, owner isolation, and safe DTOs.
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
from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_FAILED_VALIDATION
from app.integrations.telegram_bot_api.errors import TelegramApiErrorKind, TelegramBotApiError
from app.integrations.telegram_bot_verify import (
    TelegramBotVerificationResult,
    TelegramTokenVerificationError,
)
from app.lib.integration_secrets_crypto import decrypt_integration_secret
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.schemas.telegram_config import bot_telegram_status_from_read
from app.services.bot_exceptions import BotForbiddenError
from app.services.telegram_config_exceptions import (
    TelegramBotAlreadyAttachedError,
    TelegramConfigNotFoundError,
    TelegramTokenInvalidError,
    TelegramWebhookRegistrationError,
)
from app.services.telegram_config_service import TelegramConfigService
from sqlalchemy import text

from tests.integration_db import integration_database_url
from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLAIN_TOKEN = "123456789:AAH_integration_test_token_value_xxx"
JWT_TEST_KEY = "z" * 32
PUBLIC_API_BASE_TEST = "https://api.test.example"

VerifyTokenCallable = Callable[..., Awaitable[TelegramBotVerificationResult]]


async def _noop_set_webhook(_token: str, _url: str, _secret: str) -> None:
    return None


async def _noop_delete_webhook(_token: str) -> None:
    return None


def _telegram_svc(
    session,
    repo,
    settings,
    *,
    verify_token: VerifyTokenCallable,
    set_bot_webhook=_noop_set_webhook,
    delete_bot_webhook=_noop_delete_webhook,
) -> TelegramConfigService:
    return TelegramConfigService(
        session,
        repo,
        settings,
        verify_token=verify_token,
        set_bot_webhook=set_bot_webhook,
        delete_bot_webhook=delete_bot_webhook,
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
def _alembic_for_telegram_config_service_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "tg-svc") -> str:
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


def _verify_ok_factory(
    *,
    telegram_bot_id: int = 424242,
    username: str = "mock_bot",
) -> tuple[list[str], VerifyTokenCallable]:
    calls: list[str] = []

    async def _verify(token: str) -> TelegramBotVerificationResult:
        calls.append(token)
        return TelegramBotVerificationResult(
            telegram_bot_id=telegram_bot_id,
            username=username,
            first_name="Mock",
        )

    return calls, _verify


def test_connect_encrypts_token_at_rest_and_verify_mock_used(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("enc")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            calls, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="TG Encrypt Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                read = await svc.connect_telegram_for_bot(owner, bot.id, f"  {PLAIN_TOKEN}  ")
                assert read.bot_username == "mock_bot"
                assert read.is_connected is True
                assert read.webhook_url is not None
                assert str(bot.id) in read.webhook_url
                assert "/public/telegram/" in read.webhook_url
                assert read.metadata_json is not None
                assert read.metadata_json.get("telegram_bot_id") == 424242

            assert calls == [PLAIN_TOKEN]

            async with sm() as session:
                raw = (
                    await session.execute(
                        text(
                            "SELECT bot_token_encrypted FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)",
                        ),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert PLAIN_TOKEN not in raw
                assert isinstance(raw, str)
                assert len(raw) > len(PLAIN_TOKEN)
                assert decrypt_integration_secret(raw, settings) == PLAIN_TOKEN
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_connect_read_model_has_no_token_leak(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("leak")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Leak Check Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                read = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            dumped = read.model_dump()
            assert "bot_token" not in dumped
            assert "bot_token_encrypted" not in dumped
            assert "token" not in dumped
            blob = read.model_dump_json()
            assert PLAIN_TOKEN not in blob
            assert "AAH_integration_test" not in blob

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                got = await svc.get_telegram_config_for_bot(owner, bot.id)
                assert got is not None
                assert PLAIN_TOKEN not in got.model_dump_json()
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_invalid_token_persists_failed_validation_without_token(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("badtok")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            async def _fail(_token: str) -> TelegramBotVerificationResult:
                raise TelegramTokenVerificationError("nope")

            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Bad Token Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=_fail)
                with pytest.raises(TelegramTokenInvalidError):
                    await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 1
                st = (
                    await session.execute(
                        text(
                            "SELECT provisioning_status, bot_token_encrypted IS NULL AS no_tok "
                            "FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"
                        ),
                        {"bid": str(bot.id)},
                    )
                ).first()
                assert st is not None
                assert str(st[0]) == TELEGRAM_PROVISIONING_FAILED_VALIDATION
                assert st[1] is True
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_short_token_rejected_without_calling_verify(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("short")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Short Tok",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            calls: list[str] = []

            async def _never_called(t: str) -> TelegramBotVerificationResult:
                calls.append(t)
                return TelegramBotVerificationResult(1, None, None)

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=_never_called)
                with pytest.raises(TelegramTokenInvalidError):
                    await svc.connect_telegram_for_bot(owner, bot.id, "short")
            assert calls == []

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 1
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_disconnect_deletes_row_second_disconnect_not_found(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("disc")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Disconnect Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 1

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                await svc.disconnect_telegram_for_bot(owner, bot.id)

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 0

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                assert await svc.get_telegram_config_for_bot(owner, bot.id) is None

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                with pytest.raises(TelegramConfigNotFoundError):
                    await svc.disconnect_telegram_for_bot(owner, bot.id)
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_non_owner_cannot_connect_or_disconnect(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_a_email = _unique_email("own-a")
    owner_b_email = _unique_email("own-b")

    async def body() -> None:
        settings = get_settings()
        owner_a = await _create_user(email=owner_a_email)
        owner_b = await _create_user(email=owner_b_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner_a.id,
                    name="A Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                with pytest.raises(BotForbiddenError):
                    await svc.connect_telegram_for_bot(owner_b, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                await svc.connect_telegram_for_bot(owner_a, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                with pytest.raises(BotForbiddenError):
                    await svc.disconnect_telegram_for_bot(owner_b, bot.id)

            async with sm() as session:
                n = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot.id)},
                    )
                ).scalar_one()
                assert int(n) == 1
        finally:
            await _delete_user_cascade(user_id=owner_a.id)
            await _delete_user_cascade(user_id=owner_b.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_get_telegram_integration_status_disconnected_and_connected(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("gistat")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Status Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                s0 = await svc.get_telegram_integration_status(owner, bot.id)
                assert s0.channel_status == "draft"
                assert s0.configured is False
                assert s0.connected is False

                read = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)
                s1 = await svc.get_telegram_integration_status(owner, bot.id)
                assert s1 == bot_telegram_status_from_read(read)
                assert s1.channel_status == "active"
                assert s1.configured is True
                assert s1.connected is True
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_non_owner_cannot_read_config(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_a_email = _unique_email("ro-a")
    owner_b_email = _unique_email("ro-b")

    async def body() -> None:
        settings = get_settings()
        owner_a = await _create_user(email=owner_a_email)
        owner_b = await _create_user(email=owner_b_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner_a.id,
                    name="Read Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                await svc.connect_telegram_for_bot(owner_a, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                with pytest.raises(BotForbiddenError):
                    await svc.get_telegram_config_for_bot(owner_b, bot.id)
        finally:
            await _delete_user_cascade(user_id=owner_a.id)
            await _delete_user_cascade(user_id=owner_b.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_start_provisioning_creates_channel_pending_without_token(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("prov-start")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Prov Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                st = await svc.start_telegram_channel_provisioning(owner, bot.id)
                assert st.channel_status == "channel_pending"
                assert st.configured is False
                assert st.connected is False

            async with sm() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT provisioning_status, bot_token_encrypted IS NULL "
                            "FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"
                        ),
                        {"bid": str(bot.id)},
                    )
                ).first()
                assert row is not None
                assert str(row[0]) == "channel_pending"
                assert row[1] is True
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


async def _boom_set_webhook(_token: str, _url: str, _secret: str) -> None:
    raise TelegramBotApiError(TelegramApiErrorKind.WEBHOOK, "webhook failed")


def test_webhook_failure_leaves_channel_pending_with_encrypted_token(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("wh-fail")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
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
                svc = _telegram_svc(
                    session,
                    repo,
                    settings,
                    verify_token=verify_fn,
                    set_bot_webhook=_boom_set_webhook,
                )
                with pytest.raises(TelegramWebhookRegistrationError):
                    await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT provisioning_status, is_connected, bot_token_encrypted IS NULL "
                            "FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"
                        ),
                        {"bid": str(bot.id)},
                    )
                ).first()
                assert row is not None
                assert str(row[0]) == "channel_pending"
                assert row[1] is False
                assert row[2] is False
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_duplicate_telegram_bot_id_on_second_bot_raises_conflict(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("dup-tg")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory(telegram_bot_id=900_001)
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot_a = await repo.create_bot(
                    owner_id=owner.id,
                    name="Bot A",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                bot_b = await repo.create_bot(
                    owner_id=owner.id,
                    name="Bot B",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                await svc.connect_telegram_for_bot(owner, bot_a.id, PLAIN_TOKEN)
                with pytest.raises(TelegramBotAlreadyAttachedError):
                    await svc.connect_telegram_for_bot(owner, bot_b.id, PLAIN_TOKEN + "b")

            async with sm() as session:
                nb = (
                    await session.execute(
                        text("SELECT COUNT(*) FROM telegram_configs WHERE bot_id = CAST(:bid AS uuid)"),
                        {"bid": str(bot_b.id)},
                    )
                ).scalar_one()
                assert int(nb) == 0
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_sync_webhook_after_failed_set_webhook_reaches_active(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("wh-sync")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="WH Sync Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc_fail = _telegram_svc(
                    session,
                    repo,
                    settings,
                    verify_token=verify_fn,
                    set_bot_webhook=_boom_set_webhook,
                )
                with pytest.raises(TelegramWebhookRegistrationError):
                    await svc_fail.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)

            async with sm() as session:
                repo = BotRepository(session)
                svc_ok = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                st = await svc_ok.sync_telegram_webhook_for_bot(owner, bot.id)
                assert st.channel_status == "active"
                assert st.connected is True
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_second_connect_updates_same_row_still_active(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("reconn")

    async def body() -> None:
        settings = get_settings()
        owner = await _create_user(email=owner_email)
        try:
            _, verify_fn = _verify_ok_factory()
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Reconnect Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = _telegram_svc(session, repo, settings, verify_token=verify_fn)
                r1 = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN)
                r2 = await svc.connect_telegram_for_bot(owner, bot.id, PLAIN_TOKEN + "rotate")
                assert r1.id == r2.id
                st = await svc.get_telegram_integration_status(owner, bot.id)
                assert st.channel_status == "active"
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())
