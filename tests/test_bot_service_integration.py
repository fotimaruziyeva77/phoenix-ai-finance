"""
Bot service integration tests (validation + ownership + lifecycle).
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
from app.repositories.bot_repository import BotRepository
from app.schemas.bots import BotCreate, BotUpdate
from app.services.bot_exceptions import BotForbiddenError, BotValidationError
from app.services.bot_service import BotService
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
def _alembic_for_bot_service_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


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


def _unique_email(prefix: str = "bot-service") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


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


async def _cleanup_user(*, user_id: uuid.UUID) -> None:
    sm = get_session_maker()
    async with sm() as session:
        user = await session.get(User, user_id)
        if user is not None:
            await session.delete(user)
            await session.commit()


class _FailingAuditService:
    async def log_entity_event(self, **kwargs) -> None:
        raise RuntimeError("audit down")


def test_bot_service_validation_and_ownership(live_db_url, monkeypatch):
    owner_email = _unique_email("owner")
    other_email = _unique_email("other")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        other = await _create_user(email=other_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                service = BotService(BotRepository(session))

                # 1) create_bot_for_user works
                created = await service.create_bot_for_user(
                    owner,
                    BotCreate(
                        name="Owner Service Bot",
                        niche_id="education",
                        goal_type="support",
                        status="active",  # should be overridden by safe default
                    ),
                )
                assert created.id is not None
                assert created.owner_id == owner.id
                assert created.status == "draft"

                # 2) invalid niche rejected
                with pytest.raises(BotValidationError):
                    await service.create_bot_for_user(
                        owner,
                        BotCreate(
                            name="Bad Niche",
                            niche_id="unknown",
                            goal_type="support",
                        ),
                    )

                # 3) invalid goal_type rejected
                with pytest.raises(BotValidationError):
                    unsafe_payload = BotCreate.model_construct(
                        name="Bad Goal",
                        niche_id="education",
                        goal_type="invalid_goal",
                        status="draft",
                        welcome_message=None,
                        tone=None,
                        language=None,
                        short_description=None,
                    )
                    await service.create_bot_for_user(
                        owner,
                        unsafe_payload,
                    )

                # Create a bot for "other" user (ownership checks).
                other_created = await service.create_bot_for_user(
                    other,
                    BotCreate(
                        name="Other Bot",
                        niche_id="services",
                        goal_type="sales",
                    ),
                )

                # 4) one user cannot access another user's bot
                with pytest.raises(BotForbiddenError):
                    await service.get_bot_for_user(owner, other_created.id)

                # 5) update works only for owner
                updated = await service.update_bot_for_user(
                    owner,
                    created.id,
                    BotUpdate(name="Owner Updated", status="active"),
                )
                assert updated.name == "Owner Updated"
                assert updated.status == "active"

                with pytest.raises(BotForbiddenError):
                    await service.update_bot_for_user(
                        owner,
                        other_created.id,
                        BotUpdate(name="Cross Owner Update"),
                    )

                # 6) archive works only for owner
                archived = await service.archive_bot_for_user(owner, created.id)
                assert archived.status == "archived"

                with pytest.raises(BotForbiddenError):
                    await service.archive_bot_for_user(owner, other_created.id)

                # Extra safety: verify other user bot is untouched.
                row = (
                    await session.execute(select(Bot).where(Bot.id == other_created.id))
                ).scalar_one()
                assert row.owner_id == other.id
                assert row.status == "draft"
        finally:
            await _cleanup_user(user_id=owner.id)
            await _cleanup_user(user_id=other.id)

    _run_async_db(live_db_url, monkeypatch, body())


def test_bot_service_actions_succeed_when_audit_hook_fails(live_db_url, monkeypatch):
    owner_email = _unique_email("owner-audit-fail")

    async def body() -> None:
        owner = await _create_user(email=owner_email)
        try:
            sm = get_session_maker()
            async with sm() as session:
                service = BotService(BotRepository(session), _FailingAuditService())

                created = await service.create_bot_for_user(
                    owner,
                    BotCreate(
                        name="Audit Fallback Bot",
                        niche_id="education",
                        goal_type="support",
                    ),
                )
                assert created.id is not None
                assert created.name == "Audit Fallback Bot"

                updated = await service.update_bot_for_user(
                    owner,
                    created.id,
                    BotUpdate(name="Audit Fallback Bot Updated", status="active"),
                )
                assert updated.name == "Audit Fallback Bot Updated"
                assert updated.status == "active"

                archived = await service.archive_bot_for_user(owner, created.id)
                assert archived.status == "archived"
        finally:
            await _cleanup_user(user_id=owner.id)

    _run_async_db(live_db_url, monkeypatch, body())
