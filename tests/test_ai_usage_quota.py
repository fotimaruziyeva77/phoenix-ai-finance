"""AI usage quota service, config, and deterministic error details."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import Settings
from app.services.ai_exceptions import AIServiceQuotaExceededError
from app.services.ai_service import AIService
from app.services.ai_usage_quota_service import AIUsageQuotaService
from tests.test_ai_service import _bot, _make_chat_and_bots, _user


def _base_settings(**kwargs: object) -> Settings:
    data = {
        "environment": "local",
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "gemini_api_key": "k",
        "ai_daily_total_tokens_soft_cap_per_bot": 0,
        "ai_monthly_total_tokens_cap_per_owner": 0,
        "ai_usage_quota_warn_fraction": 0.9,
    }
    data.update(kwargs)
    return Settings.model_validate(data)


@pytest.mark.asyncio
async def test_assert_can_consume_owner_monthly_blocks_before_bot_query() -> None:
    settings = _base_settings(
        ai_monthly_total_tokens_cap_per_owner=100,
        ai_daily_total_tokens_soft_cap_per_bot=50,
    )
    repo = AsyncMock()
    repo.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=100)
    repo.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=0)
    svc = AIUsageQuotaService(repo, settings)

    with pytest.raises(AIServiceQuotaExceededError) as ei:
        await svc.assert_can_consume(bot_id=uuid.uuid4(), owner_id=uuid.uuid4())

    repo.sum_tokens_total_for_bot_on_utc_date.assert_not_awaited()
    d = ei.value.details or {}
    assert d.get("quota_scope") == "owner_monthly"
    assert d.get("used_tokens") == 100
    assert d.get("cap_tokens") == 100
    assert d.get("measure") == "tokens_total"
    assert "resets_at_utc" in d
    assert ei.value.ai_category == "quota_exceeded"


@pytest.mark.asyncio
async def test_assert_can_consume_bot_daily_blocks_when_owner_under_cap() -> None:
    settings = _base_settings(
        ai_monthly_total_tokens_cap_per_owner=10_000,
        ai_daily_total_tokens_soft_cap_per_bot=40,
    )
    repo = AsyncMock()
    repo.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=0)
    repo.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=40)
    svc = AIUsageQuotaService(repo, settings)

    with pytest.raises(AIServiceQuotaExceededError) as ei:
        await svc.assert_can_consume(bot_id=uuid.uuid4(), owner_id=uuid.uuid4())

    assert (ei.value.details or {}).get("quota_scope") == "bot_daily"


@pytest.mark.asyncio
async def test_assert_can_consume_under_caps_no_error() -> None:
    settings = _base_settings(
        ai_monthly_total_tokens_cap_per_owner=100,
        ai_daily_total_tokens_soft_cap_per_bot=50,
    )
    repo = AsyncMock()
    repo.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=10)
    repo.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=20)
    svc = AIUsageQuotaService(repo, settings)
    await svc.assert_can_consume(bot_id=uuid.uuid4(), owner_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_near_cap_emits_structured_log() -> None:
    settings = _base_settings(
        ai_monthly_total_tokens_cap_per_owner=0,
        ai_daily_total_tokens_soft_cap_per_bot=100,
        ai_usage_quota_warn_fraction=0.9,
    )
    repo = AsyncMock()
    repo.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=95)
    svc = AIUsageQuotaService(repo, settings)
    with patch("app.services.ai_usage_quota_service._LOG") as log:
        await svc.assert_can_consume(bot_id=uuid.uuid4(), owner_id=uuid.uuid4())
    near = [
        c.kwargs
        for c in log.info.call_args_list
        if getattr(c, "kwargs", None) and c.kwargs.get("metric_event") == "ai_usage_near_cap"
    ]
    assert len(near) == 1
    assert near[0].get("quota_scope") == "bot_daily"


@pytest.mark.asyncio
async def test_get_quota_read_includes_resets_and_enforced_flags() -> None:
    settings = _base_settings(
        ai_daily_total_tokens_soft_cap_per_bot=1000,
        ai_monthly_total_tokens_cap_per_owner=50_000,
    )
    repo = AsyncMock()
    repo.sum_tokens_total_for_bot_on_utc_date = AsyncMock(return_value=3)
    repo.sum_tokens_total_for_owner_in_utc_month = AsyncMock(return_value=7)
    svc = AIUsageQuotaService(repo, settings)
    out = await svc.get_quota_read(bot_id=uuid.uuid4(), owner_id=uuid.uuid4())
    assert out.bot_daily.enforced is True
    assert out.bot_daily.used_tokens == 3
    assert out.bot_daily.cap_tokens == 1000
    assert out.bot_daily.resets_at_utc is not None
    assert out.owner_monthly.enforced is True
    assert out.owner_monthly.cap_tokens == 50_000
    assert out.owner_monthly.resets_at_utc is not None


def test_utc_month_window_bounds_jan_to_feb() -> None:
    start, end = AIUsageQuotaService.utc_month_window_bounds(2026, 1)
    assert start.year == 2026 and start.month == 1 and start.day == 1
    assert end.year == 2026 and end.month == 2 and end.day == 1


@pytest.mark.asyncio
async def test_aiservice_strict_env_without_quota_repo_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _base_settings(
        environment="local",
        ai_daily_total_tokens_soft_cap_per_bot=100,
        ai_monthly_total_tokens_cap_per_owner=1_000_000,
    )
    monkeypatch.setattr(
        Settings,
        "deploy_environment_is_strict",
        property(lambda self: True),
    )
    u = _user()
    b = _bot(owner_id=u.id)
    conv_id = uuid.uuid4()
    user_mid = uuid.uuid4()
    chat, bots = _make_chat_and_bots(conv_id=conv_id, user_mid=user_mid, asst_mid=uuid.uuid4())
    bots.get_bot_by_id = AsyncMock(return_value=b)
    svc = AIService(chat, bots, settings=settings, usage_quota_repo=None)
    with pytest.raises(AIServiceQuotaExceededError) as ei:
        await svc.send_bot_message(b, u, "hello")
    assert (ei.value.details or {}).get("quota_scope") == "configuration"
    chat.add_message.assert_not_awaited()
