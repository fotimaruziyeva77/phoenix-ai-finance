# Refresh session rollout

## Deploy steps

1. Run Alembic to head so `refresh_sessions` exists: `alembic upgrade head` (revision `a1b2c3d4e5f8`).
2. Restart API workers so all instances use the new auth code paths.

## Client impact

- **Existing refresh JWTs** issued before this change have **no matching row** in `refresh_sessions`. Refresh will return **401** (`invalid_refresh_token`) until the user **signs in again** (register/login/OAuth).
- Clients should handle `refresh_token_reuse_detected` and `refresh_token_revoked` like other auth failures: clear local tokens and send the user to login.
- New endpoints: `GET /api/v1/auth/sessions`, `POST /api/v1/auth/logout-current` (body: `refresh_token`), `POST /api/v1/auth/logout-all` (Bearer access).

## Operations

- Security-relevant events are logged via `auth_audit` (`auth.refresh` with `extra.security_event` on reuse) and structured logs (`refresh_token_reuse_detected`).
