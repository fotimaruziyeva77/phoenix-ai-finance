"""Redis-backed identical-message window + consecutive streak (shared across workers)."""

from __future__ import annotations

import redis.asyncio as redis

from app.core.limiters.outcome import RateLimitOutcome
from app.core.logging import get_logger

_LOG = get_logger(__name__)

_STREAK_LUA = """
local k = KEYS[1]
local fp = ARGV[1]
local lim = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local v = redis.call('GET', k)
local count = 1
if v then
  local bar = string.find(v, '|', 1, true)
  if bar then
    local p = string.sub(v, 1, bar - 1)
    local c = tonumber(string.sub(v, bar + 1))
    if p == fp and c then
      count = c + 1
    end
  end
end
redis.call('SET', k, fp .. '|' .. count, 'EX', ttl)
if count >= lim then
  return {0}
end
return {1}
"""


class RedisWidgetStreakTracker:
    """Atomic consecutive-identical fingerprint counter per key."""

    def __init__(self, client: redis.Redis, *, key_prefix: str = "bf:wg:str:") -> None:
        self._r = client
        self._prefix = key_prefix
        self._sha: str | None = None

    def _key(self, logical_key: str) -> str:
        return f"{self._prefix}{logical_key}"

    async def _ensure_script(self) -> None:
        if self._sha is None:
            self._sha = await self._r.script_load(_STREAK_LUA)

    async def check_and_record(
        self,
        logical_key: str,
        fingerprint: str,
        *,
        limit: int,
        ttl_seconds: int = 3600,
    ) -> RateLimitOutcome:
        if limit <= 0:
            return RateLimitOutcome(allowed=True)
        await self._ensure_script()
        rk = self._key(logical_key)
        try:
            res = await self._r.evalsha(
                self._sha,
                1,
                rk,
                fingerprint,
                str(limit),
                str(ttl_seconds),
            )
        except redis.RedisError as e:
            _LOG.warning(
                "widget_abuse_redis_error",
                kind="consecutive_streak",
                error_type=type(e).__name__,
                message=str(e),
                metric_event="widget_abuse_redis_failure",
            )
            raise
        allowed = int(res[0]) == 1 if res else True
        if allowed:
            return RateLimitOutcome(allowed=True)
        return RateLimitOutcome(allowed=False, retry_after_seconds=60)
