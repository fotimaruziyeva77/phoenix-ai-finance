"""Async PostgreSQL probes for refresh-session and usage rows (integration tests)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.models.ai_foundation import AIUsageLog
from app.models.refresh_session import RefreshSession
from app.services.refresh_session_constants import (
    REVOKE_REASON_FAMILY_INVALIDATED,
    REVOKE_REASON_LOGOUT,
    REVOKE_REASON_LOGOUT_ALL,
    REVOKE_REASON_ROTATED,
)

from tests.integration.auth_setup import JWT_INTEGRATION_KEY


async def _session_rows_by_jtis(jtis: Sequence[str], live_db_url: str, monkeypatch: pytest.MonkeyPatch) -> list[RefreshSession]:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    sm = get_session_maker()
    async with sm() as session:
        result = await session.execute(select(RefreshSession).where(RefreshSession.jti.in_(list(jtis))))
        return list(result.scalars().all())


def refresh_rows_by_jtis(
    jtis: Sequence[str],
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> list[RefreshSession]:
    import asyncio

    return asyncio.run(_session_rows_by_jtis(jtis, live_db_url, monkeypatch))


async def insert_ai_usage_log_for_bot(
    *,
    bot_id: uuid.UUID,
    tokens_total: int,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    from datetime import UTC, datetime

    sm = get_session_maker()
    async with sm() as session:
        log = AIUsageLog(
            id=uuid.uuid4(),
            bot_id=bot_id,
            conversation_id=None,
            message_id=None,
            provider_name="gemini",
            model_name="gemini-2.5-flash",
            tokens_input=tokens_total,
            tokens_output=0,
            tokens_total=tokens_total,
            latency_ms=None,
            cost_usd=None,
            success=True,
            error_code=None,
            created_at=datetime.now(UTC),
        )
        session.add(log)
        await session.commit()
    await dispose_engine()
    get_settings.cache_clear()


__all__ = [
    "REVOKE_REASON_FAMILY_INVALIDATED",
    "REVOKE_REASON_LOGOUT",
    "REVOKE_REASON_LOGOUT_ALL",
    "REVOKE_REASON_ROTATED",
    "insert_ai_usage_log_for_bot",
    "refresh_rows_by_jtis",
]
