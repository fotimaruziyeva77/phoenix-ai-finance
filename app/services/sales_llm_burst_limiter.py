"""
Per-bot short-window counter for sales LLM invocations (intent + chat).

Uses the shared Redis client when configured; otherwise counters are disabled (fail-open).
"""

from __future__ import annotations

import time
import uuid

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.ai_chat_input_filter import handle_trivial_message
from app.services.intent_rule_engine import is_rule_engine_opening_or_ack

_LOG = get_logger(__name__)


def is_sales_opening_style_message(text: str, *, bot_language: str | None = None) -> bool:
    """
    True for trivial greetings / emoji pings or high-confidence rule greeting / short ack.

    Used to decide whether burst protection may return a canned line instead of chat LLM.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    if handle_trivial_message(raw, bot_language=bot_language) is not None:
        return True
    return is_rule_engine_opening_or_ack(raw)


class SalesLLMBurstLimiter:
    """Fixed-window INCR in Redis (``floor(time/window)`` bucket)."""

    def __init__(self, settings: Settings, redis_client: object | None) -> None:
        self._settings = settings
        self._redis = redis_client

    @classmethod
    def from_settings(cls, settings: Settings) -> SalesLLMBurstLimiter:
        from app.core.redis_client import get_redis_client

        return cls(settings, get_redis_client())

    def _bucket_key(self, bot_id: uuid.UUID) -> str | None:
        if self._redis is None:
            return None
        window = max(1, int(self._settings.ai_sales_llm_burst_window_seconds))
        bucket = int(time.time()) // window
        pfx = (self._settings.ai_sales_llm_burst_redis_key_prefix or "bf:ai:llmburst").strip() or "bf:ai:llmburst"
        return f"{pfx}:v1:{bot_id}:{bucket}"

    async def read_window_count(self, bot_id: uuid.UUID) -> int:
        key = self._bucket_key(bot_id)
        if key is None:
            return 0
        try:
            raw = await self._redis.get(key)  # type: ignore[union-attr]
            return int(raw or 0)
        except Exception:
            _LOG.warning("sales_llm_burst_read_failed", bot_id=str(bot_id), exc_info=True)
            return 0

    async def record_llm_invocation(self, bot_id: uuid.UUID) -> int:
        """Increment after a real intent or chat Gemini call is issued. Returns count in bucket."""
        key = self._bucket_key(bot_id)
        if key is None:
            return 0
        window = max(1, int(self._settings.ai_sales_llm_burst_window_seconds))
        try:
            n = int(await self._redis.incr(key))  # type: ignore[union-attr]
            if n == 1:
                await self._redis.expire(key, window + 5)  # type: ignore[union-attr]
            return n
        except Exception:
            _LOG.warning("sales_llm_burst_incr_failed", bot_id=str(bot_id), exc_info=True)
            return 0

    async def should_skip_chat_llm_for_burst(
        self,
        bot_id: uuid.UUID,
        text: str,
        *,
        bot_language: str | None = None,
    ) -> bool:
        if not self._settings.ai_sales_llm_burst_protection_enabled:
            return False
        if not is_sales_opening_style_message(text, bot_language=bot_language):
            return False
        cap = max(1, int(self._settings.ai_sales_llm_burst_max_calls_per_window))
        n = await self.read_window_count(bot_id)
        return n >= cap


__all__ = ["SalesLLMBurstLimiter", "is_sales_opening_style_message"]
