"""
Utilities for bot-builder HTTP integration tests against the real FastAPI app and PostgreSQL.

Telegram Bot API calls (getMe, setWebhook) are stubbed at the :class:`~app.services.telegram_config_service.TelegramConfigService`
injection boundary so suites run offline; :class:`~app.services.bot_service.BotService`, repositories, and ORM persistence stay real.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from app.api.deps import get_telegram_config_service
from app.core.config import Settings, get_settings
from app.core.db import get_session_maker
from app.integrations.telegram_bot_verify import TelegramBotVerificationResult, TelegramTokenVerificationError
from app.main import app
from app.models.bot import Bot
from app.models.telegram_config import TelegramConfig
from app.repositories.bot_repository import BotRepository
from app.services.telegram_config_service import TelegramConfigService
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.telegram_fernet_test_key import TELEGRAM_FERNET_INTEGRATION_KEY

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Default public API base used by webhook URL construction in TelegramConfigService.
DEFAULT_PUBLIC_API_BASE_INTEGRATION = "https://api.bot-builder.integration.test"

# Token shape accepted by ``_stub_verify_telegram_token`` below (and rejected if it contains ``___BAD___``).
DEFAULT_VALID_TELEGRAM_TOKEN_FOR_TESTS = "123456789:AAH_bot_builder_e2e_integration_xx"


def alembic_upgrade_head(database_url: str) -> None:
    """Apply Alembic migrations to ``database_url`` (mutates ``DATABASE_URL`` env temporarily)."""
    import os

    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
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


def stub_verify_telegram_token(token: str) -> Any:
    """Offline stand-in for Telegram getMe (mirrors ``test_bot_create_lifecycle_integration``)."""
    if "___BAD___" in token:
        raise TelegramTokenVerificationError("bad")
    return TelegramBotVerificationResult(
        telegram_bot_id=888001,
        username="builder_e2e_bot",
        first_name="E2E",
    )


async def noop_set_webhook(_token: str, url: str, _secret: str) -> None:
    assert url.startswith("http")


async def noop_delete_webhook(_token: str) -> None:
    pass


def build_telegram_service_override(
    *,
    verify_token: Callable[[str], Any] | None = None,
) -> Any:
    """Return a FastAPI dependency override for :func:`app.api.deps.get_telegram_config_service`."""
    verify = verify_token or stub_verify_telegram_token

    def _settings_for_dep() -> Settings:
        return get_settings()

    from app.core.db import get_db

    def _override_telegram_config_service(
        session: AsyncSession = Depends(get_db),
        settings: Settings = Depends(_settings_for_dep),
    ) -> TelegramConfigService:
        return TelegramConfigService(
            session,
            BotRepository(session),
            settings,
            verify_token=verify,
            set_bot_webhook=lambda t, u, s: noop_set_webhook(t, u, s),
            delete_bot_webhook=noop_delete_webhook,
        )

    return _override_telegram_config_service


def unique_email(prefix: str = "builder_e2e") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def register_access_token(client: TestClient, email: str, *, password: str = "password123") -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Bot builder E2E"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def pick_visible_niche_and_goal(catalog: dict[str, Any]) -> tuple[str, str]:
    """Choose a niche id and a goal from the live catalog (mirrors UI niche + goal steps)."""
    niches = catalog.get("niches") or []
    for n in niches:
        if not n.get("visible", True):
            continue
        goals = n.get("supported_goals") or []
        if goals:
            return str(n["id"]), str(goals[0])
    raise AssertionError("catalog/niches returned no visible niche with supported_goals")


async def fetch_bot_row(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    bot_id: uuid.UUID,
) -> Bot | None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        return await session.get(Bot, bot_id)


async def fetch_telegram_config_row(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    bot_id: uuid.UUID,
) -> TelegramConfig | None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        stmt = select(TelegramConfig).where(TelegramConfig.bot_id == bot_id).limit(1)
        return (await session.execute(stmt)).scalar_one_or_none()


async def count_bots_for_owner(
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    owner_id: uuid.UUID,
) -> int:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        n = await session.scalar(select(func.count(Bot.id)).where(Bot.owner_id == owner_id))
        return int(n or 0)


def attach_telegram_override() -> None:
    app.dependency_overrides[get_telegram_config_service] = build_telegram_service_override()


def detach_telegram_override() -> None:
    app.dependency_overrides.pop(get_telegram_config_service, None)


def builder_client_teardown() -> None:
    import asyncio

    from app.core.db import dispose_engine

    detach_telegram_override()
    asyncio.run(dispose_engine())
    get_settings.cache_clear()
