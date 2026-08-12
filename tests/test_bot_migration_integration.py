"""
Bot migration verification tests.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import get_settings
from app.core.db import normalize_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
def _alembic_for_bot_migration_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def test_bot_migration_applies_to_script_head(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def body() -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        expected_head = ScriptDirectory.from_config(cfg).get_current_head()
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


def test_bots_table_columns_and_constraints_exist(live_db_url: str) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                columns = await conn.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='bots'
                        ORDER BY ordinal_position
                        """
                    )
                )
                col_names = [str(row[0]) for row in columns.fetchall()]
                assert col_names == [
                    "id",
                    "owner_id",
                    "name",
                    "niche_id",
                    "goal_type",
                    "status",
                    "welcome_message",
                    "tone",
                    "language",
                    "short_description",
                    "created_at",
                    "updated_at",
                    "provider_name",
                    "model_name",
                    "temperature",
                    "max_output_tokens",
                    "platform_suspended_at",
                    "platform_suspension_reason",
                ]

                checks = await conn.execute(
                    text(
                        """
                        SELECT conname
                        FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        WHERE t.relname = 'bots' AND c.contype = 'c'
                        ORDER BY conname
                        """
                    )
                )
                check_names = [str(row[0]) for row in checks.fetchall()]
                assert "ck_bots_status_allowed" in check_names
                assert "ck_bots_goal_type_allowed" in check_names
        finally:
            await engine.dispose()

    asyncio.run(body())
