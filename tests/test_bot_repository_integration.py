"""
Bot repository integration tests (PostgreSQL + migrations).
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
from app.core.db import dispose_engine, get_session_maker
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.bot_repository import BotListFilters, BotRepository
from sqlalchemy import select

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
def _alembic_for_bot_repository_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "bot-repo") -> str:
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


async def _cleanup_user_and_bots(*, user_id: uuid.UUID) -> None:
    sm = get_session_maker()
    async with sm() as session:
        owner = await session.get(User, user_id)
        if owner is not None:
            await session.delete(owner)
            await session.commit()


def test_bot_repository_owner_scoped_crud_and_archive(live_db_url, monkeypatch):
    owner_email = _unique_email("repo-owner")
    another_email = _unique_email("repo-other")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        other = await _create_user(email=another_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                repo = BotRepository(session)

                # 1) create_bot works
                created = await repo.create_bot(
                    owner_id=owner.id,
                    name="Owner Bot A",
                    niche_id="services_local",
                    goal_type="sales",
                    status="draft",
                    welcome_message="Hello",
                    tone="friendly",
                    language="en",
                    short_description="Owner lead bot",
                )
                await repo.commit()
                assert created.id is not None

                # Add one bot for another owner (for scoping checks).
                other_bot = await repo.create_bot(
                    owner_id=other.id,
                    name="Other Bot",
                    niche_id="education",
                    goal_type="support",
                    status="active",
                )
                await repo.commit()
                assert other_bot.id is not None

                # 2) get_bot_by_id works
                fetched = await repo.get_bot_by_id(owner_id=owner.id, bot_id=created.id)
                assert fetched is not None
                assert fetched.id == created.id
                assert fetched.owner_id == owner.id

                # 3) list_bots_by_owner returns only owner bots
                owner_bots = await repo.list_bots_by_owner(owner_id=owner.id)
                assert len(owner_bots) == 1
                assert owner_bots[0].id == created.id
                assert all(b.owner_id == owner.id for b in owner_bots)

                # 4) update_bot works
                updated = await repo.update_bot(
                    owner_id=owner.id,
                    bot_id=created.id,
                    name="Owner Bot A+",
                    status="active",
                    short_description="Updated",
                )
                await repo.commit()
                assert updated is not None
                assert updated.name == "Owner Bot A+"
                assert updated.status == "active"
                assert updated.short_description == "Updated"

                # 5) archive behavior works (soft archive status)
                archived = await repo.archive_bot(owner_id=owner.id, bot_id=created.id)
                await repo.commit()
                assert archived is not None
                assert archived.status == "archived"

                # default list excludes archived
                visible_after_archive = await repo.list_bots_by_owner(owner_id=owner.id)
                assert visible_after_archive == []

                # include_archived can fetch it
                all_after_archive = await repo.list_bots_by_owner(
                    owner_id=owner.id,
                    filters=BotListFilters(include_archived=True),
                )
                assert len(all_after_archive) == 1
                assert all_after_archive[0].status == "archived"

                # exists_for_owner reflects owner scoping
                assert await repo.exists_for_owner(owner_id=owner.id, bot_id=created.id) is True
                assert await repo.exists_for_owner(owner_id=owner.id, bot_id=other_bot.id) is False

                # 6) one user cannot fetch another user bot via owner-scoped methods
                cross = await repo.get_bot_by_id(owner_id=owner.id, bot_id=other_bot.id)
                assert cross is None

                # update across owner boundary should do nothing
                forbidden_update = await repo.update_bot(
                    owner_id=owner.id,
                    bot_id=other_bot.id,
                    name="Hacked",
                )
                assert forbidden_update is None

                # archive across owner boundary should do nothing
                forbidden_archive = await repo.archive_bot(
                    owner_id=owner.id,
                    bot_id=other_bot.id,
                )
                assert forbidden_archive is None

                # Verify other bot remains unchanged
                stmt = select(Bot).where(Bot.id == other_bot.id)
                row = (await session.execute(stmt)).scalar_one()
                assert row.owner_id == other.id
                assert row.name == "Other Bot"
                assert row.status == "active"
        finally:
            await _cleanup_user_and_bots(user_id=owner.id)
            await _cleanup_user_and_bots(user_id=other.id)

    _run_async_db(live_db_url, monkeypatch, body())
