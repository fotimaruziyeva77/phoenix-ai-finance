# Distributed rate limiting (Redis)

## Algorithm

**Sliding window** counts are stored in a Redis **sorted set** per logical key. Each accepted request adds a member scored with server time in milliseconds (`Redis TIME`), after trimming members older than the window. If cardinality is already at `limit`, the request is rejected and **retry-after** is derived from the oldest score still in the window (ceil to whole seconds). A **Lua script** runs trim → count → optional add atomically so limits stay correct under concurrent workers.

**Widget consecutive-identical** streaks use a **string** key (`fingerprint|count`) with TTL, updated in Lua so two workers cannot desynchronize the streak.

## Degraded Redis

- **Auth, OAuth, knowledge upload rate checks:** default **fail closed** (`503`) when `APP_RATE_LIMIT_AUTH_FAIL_CLOSED_ON_REDIS_ERROR` is true (default). Set to false to allow traffic if Redis errors (not recommended for production auth).
- **Public widget** coarse limits and abuse heuristics: default **fail open** when `APP_RATE_LIMIT_PUBLIC_FAIL_OPEN_ON_REDIS_ERROR` is true (default) so the widget stays available; set to false to return `503` on Redis errors.

## Configuration

See `Settings` in `app/core/config.py`: `rate_limit_redis_url` (aliases include `REDIS_URL`), `rate_limit_redis_key_prefix`, timeouts, and the two fail-open / fail-closed flags. Per-endpoint numeric limits remain the existing `APP_RATE_LIMIT_*` variables.

If `rate_limit_redis_url` is unset or startup ping fails, the API falls back to an **in-memory** sliding window (single-process only).
