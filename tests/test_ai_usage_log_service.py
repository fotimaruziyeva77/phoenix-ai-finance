"""Unit tests for :class:`~app.services.ai_usage_log_service.AIUsageLogService`."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

from app.repositories.ai_chat_repository import AIChatRepository
from app.schemas.ai_usage import AI_USAGE_STEP_CHAT_COMPLETION, AIUsageLogPayload
from app.services.ai_usage_log_service import AIUsageLogService


def test_record_delegates_to_repository() -> None:
    async def run() -> None:
        log_id = uuid.uuid4()
        mock_row = AsyncMock()
        mock_row.id = log_id

        chat = AsyncMock(spec=AIChatRepository)
        chat.add_usage_log = AsyncMock(return_value=mock_row)

        svc = AIUsageLogService(chat)
        payload = AIUsageLogPayload(
            bot_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            message_id=None,
            provider_name="gemini",
            model_name="m",
            tokens_input=1,
            tokens_output=2,
            tokens_total=3,
            latency_ms=50,
            cost_usd=Decimal("0.01"),
            success=True,
            error_code=None,
        )
        out = await svc.record(payload)
        assert out is mock_row
        chat.add_usage_log.assert_awaited_once()
        kw = chat.add_usage_log.await_args.kwargs
        assert kw["bot_id"] == payload.bot_id
        assert kw["conversation_id"] == payload.conversation_id
        assert kw["message_id"] is None
        assert kw["provider_name"] == "gemini"
        assert kw["model_name"] == "m"
        assert kw["tokens_input"] == 1
        assert kw["tokens_output"] == 2
        assert kw["tokens_total"] == 3
        assert kw["latency_ms"] == 50
        assert kw["cost_usd"] == Decimal("0.01")
        assert kw["success"] is True
        assert kw["error_code"] is None
        assert kw.get("step_kind") is None

    asyncio.run(run())


def test_record_passes_step_kind() -> None:
    async def run() -> None:
        chat = AsyncMock(spec=AIChatRepository)
        chat.add_usage_log = AsyncMock(return_value=AsyncMock())
        svc = AIUsageLogService(chat)
        payload = AIUsageLogPayload(
            bot_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            message_id=None,
            provider_name="gemini",
            model_name="m",
            tokens_input=1,
            tokens_output=1,
            tokens_total=2,
            latency_ms=10,
            cost_usd=Decimal("0"),
            success=True,
            error_code=None,
            step_kind=AI_USAGE_STEP_CHAT_COMPLETION,
        )
        await svc.record(payload)
        assert chat.add_usage_log.await_args.kwargs["step_kind"] == AI_USAGE_STEP_CHAT_COMPLETION

    asyncio.run(run())


def test_record_failed_request_passes_error_and_success_false() -> None:
    """Failed inference calls must still persist a usage row with error metadata."""

    async def run() -> None:
        chat = AsyncMock(spec=AIChatRepository)
        chat.add_usage_log = AsyncMock(return_value=AsyncMock())

        svc = AIUsageLogService(chat)
        payload = AIUsageLogPayload(
            bot_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            message_id=None,
            provider_name="gemini",
            model_name="m",
            tokens_input=0,
            tokens_output=0,
            tokens_total=0,
            latency_ms=1200,
            cost_usd=None,
            success=False,
            error_code="rate_limited",
        )
        await svc.record(payload)
        kw = chat.add_usage_log.await_args.kwargs
        assert kw["success"] is False
        assert kw["error_code"] == "rate_limited"
        assert kw["message_id"] is None
        assert kw["tokens_total"] == 0
        assert kw["cost_usd"] is None
        assert kw["latency_ms"] == 1200

    asyncio.run(run())
