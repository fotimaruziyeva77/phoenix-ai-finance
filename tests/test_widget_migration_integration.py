"""
``widget_configs`` migration verification (PostgreSQL + Alembic head).

Checks clean apply alignment, table presence, uniqueness, and FK delete rules.
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
def _alembic_for_widget_migration_tests() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


def test_widget_migration_applies_to_script_head(live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_widget_configs_table_columns_uniques_and_fk_cascade(live_db_url: str) -> None:
    async def body() -> None:
        engine = create_async_engine(normalize_database_url(live_db_url), pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_schema = 'public' AND table_name = 'widget_configs'"
                        )
                    )
                ).first()
                assert row is not None

                columns = await conn.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema='public' AND table_name='widget_configs'
                        ORDER BY ordinal_position
                        """
                    )
                )
                col_names = [str(r[0]) for r in columns.fetchall()]
                assert col_names == [
                    "id",
                    "bot_id",
                    "owner_id",
                    "public_widget_key",
                    "is_enabled",
                    "allowed_domains_json",
                    "theme",
                    "welcome_text",
                    "widget_settings_json",
                    "created_at",
                    "updated_at",
                ]

                uq = await conn.execute(
                    text(
                        """
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uq_widget_configs_public_widget_key'
                          AND contype = 'u'
                        """
                    )
                )
                assert uq.first() is not None

                fk_rows = (
                    await conn.execute(
                        text(
                            """
                            SELECT kcu.column_name, ccu.table_name AS ref_table, rc.delete_rule
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON tc.constraint_name = kcu.constraint_name
                             AND tc.table_schema = kcu.table_schema
                            JOIN information_schema.constraint_column_usage ccu
                              ON ccu.constraint_name = tc.constraint_name
                             AND ccu.table_schema = tc.table_schema
                            JOIN information_schema.referential_constraints rc
                              ON rc.constraint_name = tc.constraint_name
                             AND rc.constraint_schema = tc.table_schema
                            WHERE tc.table_schema = 'public'
                              AND tc.table_name = 'widget_configs'
                              AND tc.constraint_type = 'FOREIGN KEY'
                            ORDER BY kcu.column_name
                            """
                        )
                    )
                ).fetchall()
                rules = {(str(r[0]), str(r[1]), str(r[2])) for r in fk_rows}
                assert ("bot_id", "bots", "CASCADE") in rules
                assert ("owner_id", "users", "CASCADE") in rules
        finally:
            await engine.dispose()

    asyncio.run(body())
