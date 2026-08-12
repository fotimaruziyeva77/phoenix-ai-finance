"""Redis-backed sliding window using a sorted set + server time (multi-instance safe)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import redis.asyncio as redis

from app.core.limiters.outcome import RateLimitOutcome
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

_LOG = get_logger(__name__)

# KEYS[1] = zset key
# ARGV[1] = now_ms
# ARGV[2] = window_ms
# ARGV[3] = limit (max entries in window)
# ARGV[4] = unique member id
# Returns: {allowed 0|1, retry_after_seconds}
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local min_score = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', min_score)
local n = redis.call('ZCARD', key)
if n >= limit then
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local oldest_score = tonumber(oldest[2])
  local retry_ms = oldest_score + window - now
  if retry_ms < 0 then retry_ms = 0 end
  return {0, math.ceil(retry_ms / 1000)}
end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, window)
return {1, 0}
"""


class RedisSlidingWindowLimiter:
    """Distributed sliding window; one Redis connection (or pool) shared by all keys."""

    def __init__(
        self,
        client: redis.Redis,
        *,
        key_prefix: str = "bf:rl:",
    ) -> None:
        self._r = client
        self._prefix = key_prefix.rstrip(":") + ":"
        self._sha: str | None = None

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def _ensure_script(self) -> None:
        if self._sha is None:
            self._sha = await self._r.script_load(_SLIDING_WINDOW_LUA)

    async def consume(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: float,
    ) -> RateLimitOutcome:
        if limit <= 0:
            return RateLimitOutcome(allowed=True)
        window_ms = int(window_seconds * 1000)
        if window_ms < 1:
            window_ms = 1

        await self._ensure_script()
        redis_key = self._full_key(key)
        try:
            now_ms = await self._r.time()
            # TIME returns [seconds, microseconds]
            ms = int(now_ms[0]) * 1000 + int(now_ms[1]) // 1000
            member = f"{ms}:{uuid.uuid4().hex}"
            res = await self._r.evalsha(
                self._sha,
                1,
                redis_key,
                str(ms),
                str(window_ms),
                str(limit),
                member,
            )
        except redis.RedisError as e:
            _LOG.warning(
                "rate_limit_redis_error",
                error_type=type(e).__name__,
                message=str(e),
            )
            raise

        # Lua integers may arrive as str when decode_responses=True; never use bool("0").
        allowed = int(res[0]) == 1
        retry_after = int(res[1]) if len(res) > 1 else 0
        if allowed:
            return RateLimitOutcome(allowed=True)
        return RateLimitOutcome(allowed=False, retry_after_seconds=max(1, retry_after))
