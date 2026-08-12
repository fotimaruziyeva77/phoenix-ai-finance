"""BotService AI settings wiring (mocked repository, no DB)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.schemas.bots import BotCreate, BotUpdate
from app.services.bot_exceptions import BotValidationError
from app.services.bot_service import BotService


def _bot_row(
    *,
    owner_id: uuid.UUID,
    bot_id: uuid.UUID | None = None,
    **kwargs: object,
) -> SimpleNamespace:
    now = datetime.now(UTC)
    bid = bot_id or uuid.uuid4()
    base: dict[str, object] = {
        "id": bid,
        "owner_id": owner_id,
        "name": "Bot",
        "niche_id": "education",
        "goal_type": "support",
        "status": "draft",
        "welcome_message": None,
        "tone": None,
        "language": None,
        "short_description": None,
        "provider_name": "gemini",
        "model_name": None,
        "temperature": None,
        "max_output_tokens": None,
        "created_at": now,
        "updated_at": now,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_create_bot_forwards_default_provider_and_null_model() -> None:
    async def run() -> None:
        owner_id = uuid.uuid4()
        user = SimpleNamespace(id=owner_id)
        repo = AsyncMock()
        created = _bot_row(owner_id=owner_id, name="N")
        repo.create_bot = AsyncMock(return_value=created)
        repo.commit = AsyncMock()
        svc = BotService(repo, audit_service=None)
        out = await svc.create_bot_for_user(
            user,
            BotCreate(name="N", niche_id="education", goal_type="support"),
        )
        assert out.provider_name == "gemini"
        assert out.model_name is None
        kw = repo.create_bot.await_args.kwargs
        assert kw["provider_name"] == "gemini"
        assert kw["model_name"] is None
        assert kw["temperature"] is None
        assert kw["max_output_tokens"] is None

    asyncio.run(run())


def test_update_bot_passes_ai_fields_to_repository() -> None:
    async def run() -> None:
        owner_id = uuid.uuid4()
        bot_id = uuid.uuid4()
        user = SimpleNamespace(id=owner_id)
        before = _bot_row(owner_id=owner_id, bot_id=bot_id)
        after = _bot_row(
            owner_id=owner_id,
            bot_id=bot_id,
            model_name="gemini-2.5-flash",
            temperature=0.5,
            max_output_tokens=1024,
        )
        repo = AsyncMock()
        repo.get_bot_by_id = AsyncMock(return_value=before)
        repo.update_bot = AsyncMock(return_value=after)
        repo.commit = AsyncMock()
        svc = BotService(repo, audit_service=None)
        payload = BotUpdate.model_validate(
            {
                "model_name": "gemini-2.5-flash",
                "temperature": 0.5,
                "max_output_tokens": 1024,
            }
        )
        out = await svc.update_bot_for_user(user, bot_id, payload)
        assert out.model_name == "gemini-2.5-flash"
        assert out.temperature == 0.5
        assert out.max_output_tokens == 1024
        ukw = repo.update_bot.await_args.kwargs
        assert ukw["provided_fields"] == {"model_name", "temperature", "max_output_tokens"}
        assert ukw["model_name"] == "gemini-2.5-flash"
        assert ukw["temperature"] == 0.5
        assert ukw["max_output_tokens"] == 1024

    asyncio.run(run())


def test_update_bot_rejects_null_provider_name() -> None:
    async def run() -> None:
        owner_id = uuid.uuid4()
        bot_id = uuid.uuid4()
        user = SimpleNamespace(id=owner_id)
        repo = AsyncMock()
        repo.get_bot_by_id = AsyncMock(return_value=_bot_row(owner_id=owner_id, bot_id=bot_id))
        svc = BotService(repo, audit_service=None)
        payload = BotUpdate.model_validate({"provider_name": None})
        with pytest.raises(BotValidationError, match="provider_name cannot be null"):
            await svc.update_bot_for_user(user, bot_id, payload)
        repo.update_bot.assert_not_awaited()

    asyncio.run(run())
