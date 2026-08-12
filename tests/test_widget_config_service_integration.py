"""
WidgetConfigService integration tests (PostgreSQL + Alembic head).

Covers get-or-create, key uniqueness across bots, updates, domain persistence, and owner scoping.
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
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.bot_repository import BotRepository
from app.schemas.widget_config import WidgetConfigUpdate
from app.services.bot_exceptions import BotForbiddenError, BotNotFoundError
from app.services.widget_config_exceptions import WidgetConfigNotFoundError, WidgetConfigValidationError
from app.services.widget_config_service import WidgetConfigService
from sqlalchemy import text

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
def _alembic_for_widget_config_service_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "widget-svc") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _run_async_db(live_db_url: str, monkeypatch: pytest.MonkeyPatch, coro) -> None:
    async def runner() -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
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


def test_get_or_create_widget_config_creates_and_is_idempotent(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("goc")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Widget GO Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                first = await svc.get_or_create_widget_config_for_bot(owner, bot.id)
                assert first.bot_id == bot.id
                assert first.owner_id == owner.id
                assert len(first.public_widget_key) >= 40

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                second = await svc.get_or_create_widget_config_for_bot(owner, bot.id)
                assert second.id == first.id
                assert second.public_widget_key == first.public_widget_key
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_public_widget_keys_unique_across_two_bots_same_owner(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("two-bots")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                b1 = await repo.create_bot(
                    owner_id=owner.id,
                    name="W1",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                b2 = await repo.create_bot(
                    owner_id=owner.id,
                    name="W2",
                    niche_id="education",
                    goal_type="faq",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                w1 = await svc.get_or_create_widget_config_for_bot(owner, b1.id)
                w2 = await svc.get_or_create_widget_config_for_bot(owner, b2.id)
                assert w1.public_widget_key != w2.public_widget_key
                assert w1.bot_id != w2.bot_id
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_update_widget_config_and_allowed_domains_persist(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("upd")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Upd Bot",
                    niche_id="retail",
                    goal_type="sales",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                await svc.get_or_create_widget_config_for_bot(owner, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                updated = await svc.update_widget_config_for_bot(
                    owner,
                    bot.id,
                    WidgetConfigUpdate(
                        allowed_domains_json=[
                            "HTTPS://WWW.Example.COM/path",
                            "partner.org",
                        ],
                        theme="  dark  ",
                        welcome_text="  Hi  ",
                        is_enabled=False,
                        widget_settings_json={"position": "bottom-right"},
                    ),
                )
                assert updated.is_enabled is False
                assert updated.theme == "dark"
                assert updated.welcome_text == "Hi"
                assert updated.allowed_domains_json == ["www.example.com", "partner.org"]
                assert updated.widget_settings_json == {"position": "bottom-right"}

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                loaded = await svc.get_widget_config_for_owner(owner, bot.id)
                assert loaded.allowed_domains_json == ["www.example.com", "partner.org"]
                assert loaded.theme == "dark"
                assert loaded.is_enabled is False

            async with sm() as session:
                raw = (
                    await session.execute(
                        text(
                            "SELECT allowed_domains_json::text FROM widget_configs "
                            "WHERE bot_id = :bid AND owner_id = :oid LIMIT 1"
                        ),
                        {"bid": bot.id, "oid": owner.id},
                    )
                ).scalar_one()
                assert json.loads(raw) == ["www.example.com", "partner.org"]
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_update_invalid_domains_raises_validation_error(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("bad-dom")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Bad Dom Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                await svc.get_or_create_widget_config_for_bot(owner, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                bad = WidgetConfigUpdate.model_construct(allowed_domains_json=["", "x.com"])
                with pytest.raises(WidgetConfigValidationError):
                    await svc.update_widget_config_for_bot(owner, bot.id, bad)
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_non_owner_cannot_get_or_create_update_or_get_widget_config(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("own")
    intruder_email = _unique_email("intr")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        intruder = await _create_user(email=intruder_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="Scoped Bot",
                    niche_id="healthcare",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                with pytest.raises(BotForbiddenError):
                    await svc.get_or_create_widget_config_for_bot(intruder, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc_o = WidgetConfigService(session, repo, get_settings())
                await svc_o.get_or_create_widget_config_for_bot(owner, bot.id)

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                with pytest.raises(BotForbiddenError):
                    await svc.update_widget_config_for_bot(
                        intruder,
                        bot.id,
                        WidgetConfigUpdate(is_enabled=False),
                    )

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                with pytest.raises(BotForbiddenError):
                    await svc.get_widget_config_for_owner(intruder, bot.id)
        finally:
            await _delete_user_cascade(user_id=intruder.id)
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_unknown_bot_id_raises_not_found(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("nf")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                with pytest.raises(BotNotFoundError):
                    await svc.get_or_create_widget_config_for_bot(owner, uuid.uuid4())
                with pytest.raises(BotNotFoundError):
                    await svc.get_widget_config_for_owner(owner, uuid.uuid4())
                with pytest.raises(BotNotFoundError):
                    await svc.update_widget_config_for_bot(
                        owner,
                        uuid.uuid4(),
                        WidgetConfigUpdate(is_enabled=True),
                    )
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_get_widget_config_not_found_when_widget_missing(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_email = _unique_email("missing-wc")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)
                bot = await repo.create_bot(
                    owner_id=owner.id,
                    name="No Widget Yet",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()

            async with sm() as session:
                repo = BotRepository(session)
                svc = WidgetConfigService(session, repo, get_settings())
                with pytest.raises(WidgetConfigNotFoundError):
                    await svc.get_widget_config_for_owner(owner, bot.id)
        finally:
            await _delete_user_cascade(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())
