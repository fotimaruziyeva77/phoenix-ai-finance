# Environment and configuration checklist

Condensed checklist for **local**, **staging**, and **production**. Authoritative tables and aliases live in [PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md) and `app/core/config.py` (`APP_` prefix; unprefixed aliases documented in Settings).

## Legend

- **R** — Required for API to start in strict tiers (`staging` / `production` / `prod`)
- **F** — Required for that feature to work
- **O** — Optional / recommended
- **Unsafe** — Must be **false** or unset in strict tiers (validation enforces)

## Local development (typical)

| Variable | Notes |
|----------|--------|
| `APP_ENVIRONMENT` | `local` or `docker` |
| `DATABASE_URL` | Postgres; use `TEST_DATABASE_URL` for pytest integration from host |
| `JWT_SECRET_KEY` | ≥ 32 chars |
| `GEMINI_API_KEY` | F — if testing real AI |
| Object storage vars | F — if testing real PDF upload |
| `APP_RATE_LIMITING_ENABLED` | Often `false` in tests |
| `NEXT_PUBLIC_API_BASE_URL` | Empty = Next rewrites to `BACKEND_INTERNAL_URL` or `http://127.0.0.1:8000` |

## Staging / production (strict)

| Area | Variables |
|------|-----------|
| **Core** | `APP_ENVIRONMENT`, `DATABASE_URL` (or `APP_DATABASE_URL`), `JWT_SECRET_KEY` (≥32) |
| **Safety** | `APP_RELOAD=false`, `APP_LOG_REQUEST_BODY=false`, `APP_EXPOSE_ERROR_DETAILS=false` (defaults OK if not overridden) |
| **Browser API** | `APP_CORS_ORIGINS` — dashboard + allowed widget embed origins (HTTPS in prod) |
| **Telegram** | `APP_PUBLIC_API_BASE_URL` — public API origin for webhooks; bot tokens via app config / DB |
| **Object storage** | Bucket, endpoint, keys, region — see PRODUCTION_ENV |
| **AI** | `GEMINI_API_KEY` (or app-prefixed alias) |
| **OAuth** | Per-provider client ID/secret + redirect URIs matching this tier |
| **Observability** | `APP_LOG_JSON`, `SENTRY_DSN` / `SENTRY_RELEASE` — O but recommended for prod |
| **Telegram token encryption** | `APP_TELEGRAM_TOKEN_FERNET_KEY` — set explicitly in prod if storing tokens |
| **Proxy trust** | `APP_TRUST_FORWARDED_FOR=true` **only** behind trusted reverse proxy |

## Frontend (build-time)

| Variable | Notes |
|----------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | Public API origin for browser/API client; **per-tier build** |

## Embed widget (runtime)

Host page passes **`apiBaseUrl`** (and public widget key) at init — not baked into bundle unless you add Vite envs. Document the correct API origin per environment.

**Origin allowlist (security):** In **staging / production**, an **empty** allowed-domains list **denies** embeds by default until domains are configured. Optional unsafe override: `APP_PUBLIC_WIDGET_ALLOW_EMPTY_ORIGIN_ALLOWLIST=true` (logged). Wildcard allowlist entries (`*.example.com`, `.example.com`) are **off** in strict tiers unless `APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS=true`. For local/tests of strict behavior: `APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST=true`. Full policy: [public-widget-origin-policy.md](../security/public-widget-origin-policy.md).

## Quick “won’t start” checks

1. Strict tier without `DATABASE_URL` or short `JWT_SECRET_KEY` → validation error at startup.
2. Telegram webhook registration without public API URL → feature misconfiguration.
3. Knowledge upload without storage → upload failures (503/validation depending on path).

## Secret handling

- Never commit `.env` with real secrets.
- Use platform secret injection; rotate JWT and Fernet keys per org policy (coordinate token invalidation).
