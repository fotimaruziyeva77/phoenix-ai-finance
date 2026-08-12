"""
Auth model integration tests (PostgreSQL + applied migrations).

Migration test notes
--------------------
- Set ``TEST_DATABASE_URL`` or ``DATABASE_URL`` to an async PostgreSQL URL
  (``postgresql+asyncpg://...``). Same variable is used by Alembic via
  ``get_settings().database_url``.
- Before assertions, migrations must be at **head** (user/oauth tables plus
  deferred triggers enforcing: ``password_hash`` NULL only when at least one
  ``oauth_accounts`` row exists). This module runs ``alembic upgrade head``
  once (module autouse fixture).
- CI/local: start Postgres, export the URL, then ``pytest -m integration``.
- To reset schema only: ``alembic downgrade base`` then ``alembic upgrade head``
  (destructive; drops app tables).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.enums import OAuthProvider, UserRole
from app.models.user import OAuthAccount, User
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
    """Apply migrations in-process (avoids subprocess + env drift on Windows)."""
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
def _alembic_upgrade_head_for_user_model_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def _unique_email(prefix: str = "user") -> str:
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


def test_user_creates_successfully_with_password_hash(live_db_url, monkeypatch):
    email = _unique_email("create")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            user = User(
                email=email,
                password_hash="bcrypt$dummy",
                full_name="Test User",
                role=UserRole.customer_admin,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            assert user.id is not None
            assert user.email == email
            assert user.password_hash == "bcrypt$dummy"
            assert user.is_verified is False

            row = await session.scalar(select(User).where(User.email == email))
            assert row is not None
            await session.delete(row)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_user_email_uniqueness_enforced(live_db_url, monkeypatch):
    email = _unique_email("dup")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            session.add(
                User(
                    email=email,
                    password_hash="h1",
                    role=UserRole.customer_admin,
                )
            )
            await session.commit()

        async with sm() as session:
            session.add(
                User(
                    email=email,
                    password_hash="h2",
                    role=UserRole.customer_admin,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with sm() as session:
            u = await session.scalar(select(User).where(User.email == email))
            assert u is not None
            await session.delete(u)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_oauth_account_provider_tuple_uniqueness(live_db_url, monkeypatch):
    email = _unique_email("oauth_dup")
    provider = OAuthProvider.github
    ext_id = f"gh-{uuid.uuid4().hex}"

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            user = User(
                email=email,
                password_hash=None,
                role=UserRole.customer_admin,
            )
            session.add(user)
            await session.flush()
            session.add(
                OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=ext_id,
                    provider_email=email,
                )
            )
            session.add(
                OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=ext_id,
                    provider_email=email,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    _run_async_db(live_db_url, monkeypatch, body())


def test_password_hash_null_without_oauth_rejected_at_commit(live_db_url, monkeypatch):
    email = _unique_email("no_oauth")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            session.add(
                User(
                    email=email,
                    password_hash=None,
                    role=UserRole.customer_admin,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    _run_async_db(live_db_url, monkeypatch, body())


def test_password_hash_null_allowed_when_oauth_linked_same_transaction(
    live_db_url, monkeypatch
):
    email = _unique_email("oauth_only")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            user = User(
                email=email,
                password_hash=None,
                role=UserRole.customer_admin,
            )
            session.add(user)
            await session.flush()
            session.add(
                OAuthAccount(
                    user_id=user.id,
                    provider=OAuthProvider.google,
                    provider_user_id=f"go-{uuid.uuid4().hex}",
                    provider_email=email,
                )
            )
            await session.commit()
            await session.refresh(user)
            assert user.password_hash is None
            assert len(user.oauth_accounts) >= 1

        async with sm() as session:
            u = await session.scalar(select(User).where(User.email == email))
            assert u is not None
            await session.delete(u)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_same_user_two_oauth_same_provider_different_external_id_ok(
    live_db_url, monkeypatch
):
    email = _unique_email("multi_oauth")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            user = User(
                email=email,
                password_hash=None,
                role=UserRole.customer_admin,
            )
            session.add(user)
            await session.flush()
            session.add_all(
                [
                    OAuthAccount(
                        user_id=user.id,
                        provider=OAuthProvider.github,
                        provider_user_id="gh-111",
                        provider_email=email,
                    ),
                    OAuthAccount(
                        user_id=user.id,
                        provider=OAuthProvider.github,
                        provider_user_id="gh-222",
                        provider_email=email,
                    ),
                ]
            )
            await session.commit()

        async with sm() as session:
            u = await session.scalar(select(User).where(User.email == email))
            assert u is not None
            await session.delete(u)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_deleting_last_oauth_with_null_password_rejected_at_commit(
    live_db_url, monkeypatch
):
    email = _unique_email("last_oauth")

    async def body() -> None:
        sm = get_session_maker()
        async with sm() as session:
            user = User(
                email=email,
                password_hash=None,
                role=UserRole.customer_admin,
            )
            session.add(user)
            await session.flush()
            oauth = OAuthAccount(
                user_id=user.id,
                provider=OAuthProvider.github,
                provider_user_id=f"gh-{uuid.uuid4().hex}",
                provider_email=email,
            )
            session.add(oauth)
            await session.commit()

        async with sm() as session:
            u = await session.scalar(select(User).where(User.email == email))
            assert u is not None
            o = await session.scalar(
                select(OAuthAccount).where(OAuthAccount.user_id == u.id)
            )
            assert o is not None
            await session.delete(o)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with sm() as session:
            u2 = await session.scalar(select(User).where(User.email == email))
            assert u2 is not None
            await session.delete(u2)
            await session.commit()

    _run_async_db(live_db_url, monkeypatch, body())


def test_alembic_migration_chain_matches_script_head(live_db_url, monkeypatch):
    """DB ``alembic_version`` matches Alembic script head (no hardcoded revision id)."""

    async def body() -> None:
        from app.core.db import normalize_database_url
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        expected_head = ScriptDirectory.from_config(cfg).get_current_head()

        url = normalize_database_url(live_db_url)
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                r = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = r.first()
                version = str(row[0]) if row else None
        finally:
            await engine.dispose()

        assert version == expected_head, (
            f"database at {version!r}, script head is {expected_head!r} — run alembic upgrade head"
        )

    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    try:
        asyncio.run(body())
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()
