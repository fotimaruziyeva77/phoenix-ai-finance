"""
Platform moderation migration + ORM persistence (PostgreSQL + Alembic head).

Verifies migration applies, new columns exist, values round-trip, and defaults keep
auth-related flags consistent for new rows.
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
from alembic.script import ScriptDirectory
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker, normalize_database_url
from app.models.audit_log import AuditLog
from app.models.bot import Bot
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit_service import USER_ACTION_SUSPENDED, USER_ENTITY_TYPE, AuditService
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_MODERATION_REVISION = "z9y8x7w6v5u4"


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
def _alembic_for_platform_moderation_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "mod") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def test_platform_moderation_migration_applies_to_script_head(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def body() -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        expected_head = ScriptDirectory.from_config(cfg).get_current_head()
        assert expected_head == PLATFORM_MODERATION_REVISION
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))).first()
                version = str(row[0]) if row else None
        finally:
            await engine.dispose()
        assert version == expected_head

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


def test_moderation_columns_exist_in_schema(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                for table, expected_cols in (
                    ("users", {"suspended_at", "suspension_reason"}),
                    ("bots", {"platform_suspended_at", "platform_suspension_reason"}),
                    ("audit_logs", {"metadata_json"}),
                ):
                    result = await conn.execute(
                        text(
                            """
                            SELECT column_name FROM information_schema.columns
                            WHERE table_schema = 'public' AND table_name = :t
                            """
                        ),
                        {"t": table},
                    )
                    found = {str(r[0]) for r in result.fetchall()}
                    missing = expected_cols - found
                    assert not missing, f"{table} missing columns: {missing}"
        finally:
            await engine.dispose()

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(body())


def test_suspension_and_audit_fields_round_trip(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())

    async def body() -> None:
        sm = get_session_maker()
        email = _unique_email("suspend")
        ts = datetime.now(UTC).replace(microsecond=0)
        reason_u = "platform policy violation"
        reason_b = "bot content policy"

        async with sm() as session:
            owner = User(
                email=email,
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
                is_active=True,
            )
            session.add(owner)
            await session.flush()
            bot = Bot(
                owner_id=owner.id,
                name="Mod Bot",
                niche_id="generic",
                goal_type="sales",
                status="active",
            )
            session.add(bot)
            await session.commit()
            owner_id, bot_id = owner.id, bot.id

        async with sm() as session:
            u = await session.get(User, owner_id)
            assert u is not None
            assert u.suspended_at is None
            assert u.suspension_reason is None
            assert u.is_active is True

            b = await session.get(Bot, bot_id)
            assert b is not None
            assert b.platform_suspended_at is None
            assert b.platform_suspension_reason is None

            u.suspended_at = ts
            u.suspension_reason = reason_u
            u.is_active = False
            b.platform_suspended_at = ts
            b.platform_suspension_reason = reason_b

            audit = AuditService(session)
            await audit.log_entity_event(
                actor_user_id=owner_id,
                action=USER_ACTION_SUSPENDED,
                entity_type=USER_ENTITY_TYPE,
                entity_id=owner_id,
                metadata_json={"reason": reason_u, "kind": "integration_test"},
            )
            await session.commit()

        async with sm() as session:
            u2 = await session.get(User, owner_id)
            assert u2 is not None
            assert u2.suspended_at == ts
            assert u2.suspension_reason == reason_u
            assert u2.is_active is False

            b2 = await session.get(Bot, bot_id)
            assert b2 is not None
            assert b2.platform_suspended_at == ts
            assert b2.platform_suspension_reason == reason_b

            log = (
                await session.execute(
                    select(AuditLog)
                    .where(AuditLog.entity_id == owner_id, AuditLog.action == USER_ACTION_SUSPENDED)
                    .order_by(AuditLog.created_at.desc())
                    .limit(1)
                )
            ).scalar_one()
            assert log.metadata_json == {"reason": reason_u, "kind": "integration_test"}

    try:
        asyncio.run(body())
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()


def test_new_rows_keep_moderation_defaults_for_consistency(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fresh users/bots must have NULL moderation fields and active users stay login-eligible."""
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())

    async def body() -> None:
        sm = get_session_maker()
        email = _unique_email("defaults")
        async with sm() as session:
            u = User(
                email=email,
                password_hash="bcrypt$dummy",
                role=UserRole.customer_admin,
            )
            session.add(u)
            await session.flush()
            b = Bot(
                owner_id=u.id,
                name="Default Mod Bot",
                niche_id="generic",
                goal_type="faq",
                status="draft",
            )
            session.add(b)
            await session.commit()
            uid, bid = u.id, b.id

        async with sm() as session:
            u2 = await session.get(User, uid)
            b2 = await session.get(Bot, bid)
            assert u2 is not None and b2 is not None
            assert u2.suspended_at is None
            assert u2.suspension_reason is None
            assert u2.is_active is True
            assert b2.platform_suspended_at is None
            assert b2.platform_suspension_reason is None

    try:
        asyncio.run(body())
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()
