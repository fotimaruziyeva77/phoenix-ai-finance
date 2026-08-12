"""
Pre-flight AI token quotas (hard caps) using persisted ``ai_usage_logs.tokens_total``.

Enforcement runs in :meth:`~app.services.ai_service.AIService.send_bot_message` **before** the user
message is persisted, so blocked requests do not consume DB chat rows.

**Counting:** ``tokens_total`` per log row (provider-reported when available; else estimated from
chars for successful completions in the AI layer). Prompt vs completion breakdown is stored on logs
but caps use **total** only for a single comparable budget.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository
from app.schemas.ai_quota import AIQuotaWindowRead, AIUsageQuotaRead
from app.services.ai_exceptions import AIServiceQuotaExceededError

_LOG = get_logger(__name__)


def _next_utc_midnight_after(day: date) -> datetime:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return start + timedelta(days=1)


def _first_day_next_month_utc(d: date) -> datetime:
    if d.month == 12:
        return datetime(d.year + 1, 1, 1, tzinfo=UTC)
    return datetime(d.year, d.month + 1, 1, tzinfo=UTC)


def _month_start_utc(d: date) -> datetime:
    return datetime(d.year, d.month, 1, tzinfo=UTC)


class AIUsageQuotaService:
    def __init__(self, repo: AIUsageAggregateRepository, settings: Settings) -> None:
        self._repo = repo
        self._settings = settings

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _quota_exceeded_details(
        self,
        *,
        scope: str,
        used: int,
        cap: int,
        resets_at: datetime,
    ) -> dict[str, Any]:
        return {
            "quota_scope": scope,
            "used_tokens": used,
            "cap_tokens": cap,
            "measure": "tokens_total",
            "resets_at_utc": resets_at.isoformat().replace("+00:00", "Z"),
            "retry_suggestion": "Wait until the quota window resets (see resets_at_utc) or contact support to raise limits.",
        }

    def _maybe_log_near_cap(
        self,
        *,
        scope: str,
        used: int,
        cap: int,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> None:
        cap_i = int(cap)
        if cap_i <= 0:
            return
        frac = float(self._settings.ai_usage_quota_warn_fraction)
        threshold = int(cap_i * frac)
        if used < cap_i and used >= threshold:
            _LOG.info(
                "ai_usage_near_cap",
                quota_scope=scope,
                used_tokens=used,
                cap_tokens=cap_i,
                bot_id=str(bot_id),
                owner_id=str(owner_id),
                metric_event="ai_usage_near_cap",
            )

    async def assert_can_consume(self, *, bot_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        now = self._now()
        today = now.date()

        owner_cap = int(self._settings.ai_monthly_total_tokens_cap_per_owner)
        if owner_cap > 0:
            used_o = await self._repo.sum_tokens_total_for_owner_in_utc_month(
                owner_id,
                year=today.year,
                month=today.month,
            )
            self._maybe_log_near_cap(
                scope="owner_monthly",
                used=used_o,
                cap=owner_cap,
                bot_id=bot_id,
                owner_id=owner_id,
            )
            if used_o >= owner_cap:
                reset_at = _first_day_next_month_utc(today)
                _LOG.warning(
                    "ai_usage_quota_blocked",
                    quota_scope="owner_monthly",
                    used_tokens=used_o,
                    cap_tokens=owner_cap,
                    bot_id=str(bot_id),
                    owner_id=str(owner_id),
                    metric_event="ai_usage_quota_exceeded",
                )
                raise AIServiceQuotaExceededError(
                    details=self._quota_exceeded_details(
                        scope="owner_monthly",
                        used=used_o,
                        cap=owner_cap,
                        resets_at=reset_at,
                    ),
                )

        bot_cap = int(self._settings.ai_daily_total_tokens_soft_cap_per_bot)
        if bot_cap > 0:
            used_b = await self._repo.sum_tokens_total_for_bot_on_utc_date(bot_id, today)
            self._maybe_log_near_cap(
                scope="bot_daily",
                used=used_b,
                cap=bot_cap,
                bot_id=bot_id,
                owner_id=owner_id,
            )
            if used_b >= bot_cap:
                reset_at = _next_utc_midnight_after(today)
                _LOG.warning(
                    "ai_usage_quota_blocked",
                    quota_scope="bot_daily",
                    used_tokens=used_b,
                    cap_tokens=bot_cap,
                    bot_id=str(bot_id),
                    owner_id=str(owner_id),
                    metric_event="ai_usage_quota_exceeded",
                )
                raise AIServiceQuotaExceededError(
                    details=self._quota_exceeded_details(
                        scope="bot_daily",
                        used=used_b,
                        cap=bot_cap,
                        resets_at=reset_at,
                    ),
                )

    async def get_quota_read(self, *, bot_id: uuid.UUID, owner_id: uuid.UUID) -> AIUsageQuotaRead:
        now = self._now()
        today = now.date()
        bot_cap = int(self._settings.ai_daily_total_tokens_soft_cap_per_bot)
        owner_cap = int(self._settings.ai_monthly_total_tokens_cap_per_owner)

        used_b = await self._repo.sum_tokens_total_for_bot_on_utc_date(bot_id, today)
        used_o = await self._repo.sum_tokens_total_for_owner_in_utc_month(
            owner_id,
            year=today.year,
            month=today.month,
        )

        bot_window = AIQuotaWindowRead(
            enforced=bot_cap > 0,
            used_tokens=used_b,
            cap_tokens=bot_cap if bot_cap > 0 else None,
            measure="tokens_total",
            resets_at_utc=_next_utc_midnight_after(today),
        )
        owner_window = AIQuotaWindowRead(
            enforced=owner_cap > 0,
            used_tokens=used_o,
            cap_tokens=owner_cap if owner_cap > 0 else None,
            measure="tokens_total",
            resets_at_utc=_first_day_next_month_utc(today),
        )
        return AIUsageQuotaRead(
            bot_id=bot_id,
            owner_id=owner_id,
            bot_daily=bot_window,
            owner_monthly=owner_window,
        )

    @staticmethod
    def utc_month_window_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        """First instant in month UTC and first instant of next month (for tests)."""
        start = datetime(year, month, 1, tzinfo=UTC)
        end = _first_day_next_month_utc(date(year, month, 1))
        return start, end
