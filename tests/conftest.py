from __future__ import annotations

import asyncio
import socket
from urllib.parse import urlparse

import pytest
from app.main import app
from fastapi.testclient import TestClient


def _postgres_tcp_reachable(database_url: str) -> bool:
    """Fallback when asyncpg is unavailable: open TCP only (weaker than a real DB probe)."""
    raw = database_url.strip()
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgres://", "postgresql://"):
        if raw.startswith(prefix):
            raw = "postgresql://" + raw.split("://", 1)[1]
            break
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except OSError:
        return False


def _asyncpg_dsn_from_sqlalchemy_url(database_url: str) -> str:
    raw = database_url.strip()
    if "+asyncpg" in raw:
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    if raw.startswith("postgres://"):
        return "postgresql://" + raw[len("postgres://") :]
    return raw


def _postgres_responds(database_url: str) -> bool:
    """
    True if Postgres accepts a short asyncpg connection (avoids ERRORs when TCP is open but DB is dead).
    """
    try:
        import asyncpg
    except ImportError:
        return _postgres_tcp_reachable(database_url)

    dsn = _asyncpg_dsn_from_sqlalchemy_url(database_url)

    async def _ping() -> None:
        conn = await asyncpg.connect(dsn=dsn, timeout=4.0)
        await conn.close()

    try:
        asyncio.run(asyncio.wait_for(_ping(), timeout=6.0))
    except Exception:
        return False
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    from tests.integration_db import integration_database_url

    url = integration_database_url()
    if url is None:
        return
    if _postgres_responds(url):
        return
    skip_unreachable = pytest.mark.skip(
        reason=(
            "PostgreSQL did not accept a connection (asyncpg probe failed); "
            "set TEST_DATABASE_URL to a live instance to run integration tests."
        ),
    )
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_unreachable)


@pytest.fixture(autouse=True)
def _clear_settings_cache_after_test():
    yield
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
