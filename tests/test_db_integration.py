"""Live PostgreSQL + Alembic checks. Set TEST_DATABASE_URL or DATABASE_URL."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_engine, normalize_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _integration_db_url() -> str | None:
    return integration_database_url()


requires_live_db = pytest.mark.skipif(
    not _integration_db_url(),
    reason=(
        "Set TEST_DATABASE_URL or host-reachable DATABASE_URL "
        "(not @postgres: from host; use 127.0.0.1)."
    ),
)


@pytest.fixture
def live_db_url() -> str:
    url = _integration_db_url()
    assert url is not None
    return url


@requires_live_db
@pytest.mark.integration
def test_async_database_connection_select_one(live_db_url: str, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()

    async def _run() -> None:
        try:
            engine = get_engine()
            assert isinstance(engine, AsyncEngine)
            async with engine.connect() as conn:
                value = (await conn.execute(text("SELECT 1"))).scalar_one()
                assert value == 1
        finally:
            await dispose_engine()

    try:
        asyncio.run(_run())
    finally:
        get_settings.cache_clear()


@requires_live_db
@pytest.mark.integration
def test_alembic_upgrade_head_applies_and_version_recorded(live_db_url: str, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = live_db_url
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

    url = normalize_database_url(live_db_url)

    async def _check_version() -> str | None:
        engine = create_async_engine(url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = result.first()
                return str(row[0]) if row else None
        finally:
            await engine.dispose()

    version = asyncio.run(_check_version())
    assert version is not None and len(version) > 0

    get_settings.cache_clear()
