"""Async-only DB layer contract (no live database required)."""

import asyncio
import inspect
from pathlib import Path

from app.core.db import dispose_engine, get_db, get_engine
from sqlalchemy.ext.asyncio import AsyncEngine


def test_get_db_is_async_generator():
    assert inspect.isasyncgenfunction(get_db)


def test_dispose_engine_is_coroutine_function():
    assert inspect.iscoroutinefunction(dispose_engine)


def test_core_db_source_avoids_sync_sqlalchemy_engine_apis():
    root = Path(__file__).resolve().parents[1]
    source = (root / "app" / "core" / "db.py").read_text(encoding="utf-8")
    assert "create_engine(" not in source
    assert "engine_from_config(" not in source
    assert "async_sessionmaker(" in source


def test_get_engine_returns_async_engine(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://unused:unused@127.0.0.1:65534/unused",
    )
    from app.core.config import get_settings

    get_settings.cache_clear()

    async def _run() -> None:
        try:
            engine = get_engine()
            assert isinstance(engine, AsyncEngine)
        finally:
            await dispose_engine()

    try:
        asyncio.run(_run())
    finally:
        get_settings.cache_clear()
