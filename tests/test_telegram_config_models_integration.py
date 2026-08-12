"""
TelegramConfig ORM integration tests (PostgreSQL + Alembic head).

Covers encrypted token storage, FK integrity, uniqueness on ``bot_id``, relations, and flags.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import Settings, get_settings
from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE, TELEGRAM_PROVISIONING_CHANNEL_PENDING
from app.core.db import dispose_engine, get_session_maker, normalize_database_url
from app.lib.telegram_token_crypto import decrypt_telegram_bot_token, encrypt_telegram_bot_token
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.telegram_config import TelegramConfig
from app.models.user import User
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import selectinload

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_CRYPTO_SETTINGS = Settings.model_construct(
    jwt_secret_key="telegram-model-test-jwt-key-min-32-chars!!",
    telegram_token_fernet_key=None,
)
_PLAIN_TOKEN = "123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


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
def _alembic_for_telegram_model_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "tg-owner") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_telegram_configs_table_exists_after_migrations(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_schema = 'public' AND table_name = 'telegram_configs'"
                        )
                    )
                ).first()
                assert row is not None
        finally:
            await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


def test_telegram_config_can_be_created_with_encrypted_token_and_flags(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ciphertext = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        assert _PLAIN_TOKEN not in ciphertext
        verified = datetime.now(UTC).replace(microsecond=0)
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-create"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Telegram Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()

                tc = TelegramConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    bot_token_encrypted=ciphertext,
                    bot_username="my_shop_bot",
                    webhook_url="https://api.example.com/v1/telegram/webhook",
                    is_connected=True,
                    last_verified_at=verified,
                    metadata_json={"telegram_bot_id": 12345},
                    provisioning_status=TELEGRAM_PROVISIONING_ACTIVE,
                )
                session.add(tc)
                await session.commit()
                tid = tc.id

            async with sm() as session:
                row = await session.get(TelegramConfig, tid)
                assert row is not None
                assert row.bot_token_encrypted == ciphertext
                assert row.bot_token_encrypted != _PLAIN_TOKEN
                assert decrypt_telegram_bot_token(row.bot_token_encrypted, _CRYPTO_SETTINGS) == _PLAIN_TOKEN
                assert row.bot_id == bot.id
                assert row.owner_id == owner.id
                assert row.bot_username == "my_shop_bot"
                assert row.webhook_url == "https://api.example.com/v1/telegram/webhook"
                assert row.is_connected is True
                assert row.last_verified_at == verified
                assert row.metadata_json == {"telegram_bot_id": 12345}
                assert row.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_config_bot_id_uniqueness_enforced(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ct = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-uq"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="One Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                session.add(
                    TelegramConfig(
                        bot_id=bot.id,
                        owner_id=owner.id,
                        bot_token_encrypted=ct,
                        provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                    ),
                )
                await session.commit()

            async with sm() as session:
                with pytest.raises(IntegrityError):
                    session.add(
                        TelegramConfig(
                            bot_id=bot.id,
                            owner_id=owner.id,
                            bot_token_encrypted=ct,
                            provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                        ),
                    )
                    await session.flush()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_config_foreign_key_rejects_invalid_bot_id(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ct = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        fake_bot = uuid.uuid4()
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-fk"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                with pytest.raises(IntegrityError):
                    session.add(
                        TelegramConfig(
                            bot_id=fake_bot,
                            owner_id=owner.id,
                            bot_token_encrypted=ct,
                            provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                        ),
                    )
                    await session.flush()
                await session.rollback()
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_config_bot_and_owner_relationships_resolve(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ct = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-rel"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Rel Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                tc = TelegramConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    bot_token_encrypted=ct,
                    is_connected=False,
                    provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                )
                session.add(tc)
                await session.commit()
                tid = tc.id

            async with sm() as session:
                row = await session.execute(
                    select(TelegramConfig)
                    .options(
                        selectinload(TelegramConfig.bot),
                        selectinload(TelegramConfig.owner),
                    )
                    .where(TelegramConfig.id == tid),
                )
                cfg = row.scalar_one()
                assert cfg.bot is not None
                assert cfg.bot.id == bot.id
                assert cfg.bot.name == "Rel Bot"
                assert cfg.owner is not None
                assert cfg.owner.id == owner.id
                assert cfg.owner.email == owner.email
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_config_cascades_when_bot_deleted(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ct = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-cascade"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Cascade Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                tc = TelegramConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    bot_token_encrypted=ct,
                    provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                )
                session.add(tc)
                await session.commit()
                tid = tc.id
                bid = bot.id

            async with sm() as session:
                b = await session.get(Bot, bid)
                assert b is not None
                await session.delete(b)
                await session.commit()

            async with sm() as session:
                assert await session.get(TelegramConfig, tid) is None
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())


def test_telegram_config_connection_flags_persist_on_update(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        get_settings.cache_clear()
        ct = encrypt_telegram_bot_token(_PLAIN_TOKEN, _CRYPTO_SETTINGS)
        try:
            sm = get_session_maker()
            async with sm() as session:
                owner = User(
                    email=_unique_email("tg-flags"),
                    password_hash="bcrypt$dummy",
                    role=UserRole.customer_admin,
                )
                session.add(owner)
                await session.flush()
                bot = Bot(
                    owner_id=owner.id,
                    name="Flags Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                session.add(bot)
                await session.flush()
                tc = TelegramConfig(
                    bot_id=bot.id,
                    owner_id=owner.id,
                    bot_token_encrypted=ct,
                    is_connected=False,
                    last_verified_at=None,
                    provisioning_status=TELEGRAM_PROVISIONING_CHANNEL_PENDING,
                )
                session.add(tc)
                await session.commit()
                tid = tc.id

            t2 = datetime.now(UTC).replace(microsecond=0)
            async with sm() as session:
                row = await session.get(TelegramConfig, tid)
                assert row is not None
                row.is_connected = True
                row.provisioning_status = TELEGRAM_PROVISIONING_ACTIVE
                row.last_verified_at = t2
                await session.commit()

            async with sm() as session:
                row = await session.get(TelegramConfig, tid)
                assert row is not None
                assert row.is_connected is True
                assert row.last_verified_at == t2
        finally:
            await dispose_engine()
            get_settings.cache_clear()

    asyncio.run(body())
