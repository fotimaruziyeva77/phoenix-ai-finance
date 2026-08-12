# Staging and production environment reference

All values are supplied via environment variables (or your platform’s secret injection). **Do not** embed secrets in images, workflow YAML, or logs.

Legend: **R** = required for API to start (strict tiers), **F** = required for that feature, **O** = optional. **D** = default in `Settings` already satisfies strict validation if the variable is **unset** (must not be overridden to an unsafe value).

## Core API (strict tiers: staging / production)

| Variable | Kind | Description |
|----------|------|-------------|
| `APP_ENVIRONMENT` | R | `staging`, `production`, or `prod` |
| `DATABASE_URL` or `APP_DATABASE_URL` | R | Async PostgreSQL URL, e.g. `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `JWT_SECRET_KEY` or `APP_JWT_SECRET_KEY` | R | ≥ 32 characters; signs access/refresh tokens and OAuth `state` |
| `APP_RELOAD` | D | Must not be `true` (default `false`) |
| `APP_LOG_REQUEST_BODY` | D | Must not be `true` (default `false`) |
| `APP_EXPOSE_ERROR_DETAILS` | D | Must not be `true` (default `false`) |
| `APP_CORS_ORIGINS` | F | Comma-separated browser origins for dashboard/widget (HTTPS origins in prod) |
| `APP_TRUST_FORWARDED_FOR` | O | Set `true` only behind a **trusted** reverse proxy (rate limits / audit IP) |
| `APP_PUBLIC_API_BASE_URL` | F | Public HTTPS origin of this API (no path); **required** for Telegram webhook registration |
| `APP_LOG_JSON` | O | `true` recommended behind log aggregators |
| `SENTRY_DSN` / `APP_SENTRY_DSN` | O | Error tracking; use separate projects for staging vs production |
| `SENTRY_RELEASE` / `APP_SENTRY_RELEASE` | O | Git SHA or semver for Sentry **release** (group issues by deploy); CI/Dockerfile bake this |
| `APP_VERSION` / `APP_APP_VERSION` | O | Semver or SHA exposed as API version / fallback when `SENTRY_RELEASE` unset |

**D (defaults):** In strict tiers you may omit `APP_RELOAD`, `APP_LOG_REQUEST_BODY`, and `APP_EXPOSE_ERROR_DETAILS` if defaults are acceptable. Setting `APP_RELOAD=true` or enabling request-body / error-detail leakage will fail validation.

## Dashboard (Next.js)

Set `NEXT_PUBLIC_*` **before** `npm run build` (values are baked into the client).

| Variable | Kind | Description |
|----------|------|-------------|
| `NEXT_PUBLIC_SENTRY_DSN` | O | Browser Sentry DSN (separate frontend project recommended) |
| `NEXT_PUBLIC_SENTRY_RELEASE` | O | Align with backend `SENTRY_RELEASE` for cross-service triage |
| `NEXT_PUBLIC_APP_ENVIRONMENT` | O | e.g. `staging`, `production` — Sentry environment tag |
| `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE` | O | Default `0`; increase only if you need browser performance samples |
| `SENTRY_AUTH_TOKEN` | F† | †CI secret for source map upload only |
| `SENTRY_ORG` / `SENTRY_PROJECT` | F† | †Sentry slugs for `next build` upload |

## Object storage (knowledge PDFs)

When any object storage field is used, configure the full set your SDK path expects (see `Settings` in `app/core/config.py`).

| Variable | F | Description |
|----------|---|-------------|
| `S3_BUCKET` / `APP_S3_BUCKET` / `APP_OBJECT_STORAGE_BUCKET` | F | Bucket name (dedicated bucket per tier recommended) |
| `S3_ENDPOINT_URL` / `APP_S3_ENDPOINT_URL` | F | S3-compatible endpoint (AWS leave unset or use regional endpoint) |
| `AWS_ACCESS_KEY_ID` / `APP_OBJECT_STORAGE_ACCESS_KEY_ID` | F | Access key |
| `AWS_SECRET_ACCESS_KEY` / `APP_OBJECT_STORAGE_SECRET_ACCESS_KEY` | F | Secret key |
| `AWS_REGION` / `APP_OBJECT_STORAGE_REGION` | O | Default `us-east-1` |
| `APP_OBJECT_STORAGE_ADDRESSING_STYLE` | O | `path` or `virtual` |

## AI provider (Gemini)

| Variable | F | Description |
|----------|---|-------------|
| `GEMINI_API_KEY` / `APP_GEMINI_API_KEY` | F | For generative features |
| `APP_GEMINI_DEFAULT_MODEL` | O | Default model id |
| `APP_GEMINI_API_BASE_URL` | O | Google Generative Language API base |

## AI cost controls (optional)

See [AI_COST_OPTIMIZATION.md](./AI_COST_OPTIMIZATION.md) for measurement queries.

| Variable | Kind | Description |
|----------|------|-------------|
| `APP_AI_SALES_USE_MODEL_FOR_INTENT_WHEN_RULES_MISS` | O | Default `false`: sales bots skip the Gemini intent classifier when rules miss (uses `sales_default`). Set `true` for legacy behavior. |
| `APP_AI_INTENT_CLASSIFIER_CACHE_TTL_SECONDS` | O | In-process intent cache TTL (`0` = off). |
| `APP_AI_INTENT_CLASSIFIER_CACHE_MAX_ENTRIES` | O | Max cached intent entries per process. |
| `APP_AI_KNOWLEDGE_CHAT_CONTEXT_TOKEN_BUDGET_FRACTION` | O | Default `0.85`: fraction of default knowledge context token budget for **non-sales** dashboard chat RAG. |

## OAuth (Google / GitHub)

Required only if those auth routes are enabled for the tier. Use **separate** OAuth apps or redirect URIs per tier.

| Variable | F | Description |
|----------|---|-------------|
| `GOOGLE_CLIENT_ID` / `APP_GOOGLE_OAUTH_CLIENT_ID` | F | Web client ID |
| `GOOGLE_CLIENT_SECRET` / `APP_GOOGLE_OAUTH_CLIENT_SECRET` | F | Client secret (server only) |
| `APP_GOOGLE_OAUTH_REDIRECT_URI` | F | Backend callback URL registered in Google Cloud Console |
| `APP_FRONTEND_OAUTH_REDIRECT_URL` | F | SPA URL handling `oauth_exchange_code` / `oauth_error` |
| `GITHUB_CLIENT_ID` / `APP_GITHUB_OAUTH_CLIENT_ID` | F | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` / `APP_GITHUB_OAUTH_CLIENT_SECRET` | F | Client secret |
| `APP_GITHUB_OAUTH_REDIRECT_URI` | F | Backend callback URL registered in GitHub |

## Telegram

| Variable | F | Description |
|----------|---|-------------|
| `APP_TELEGRAM_TOKEN_FERNET_KEY` | O | Encrypts stored bot tokens; **set explicitly** in production (independent from JWT rotation) |
| `TELEGRAM_LEAD_ALERT_BOT_TOKEN` / `APP_TELEGRAM_LEAD_ALERT_BOT_TOKEN` | O | Optional internal alerts bot |
| `TELEGRAM_LEAD_ALERT_CHAT_ID` / `APP_TELEGRAM_LEAD_ALERT_CHAT_ID` | O | Target chat for alerts |

## Service URLs (conceptual checklist)

Per tier, define and document:

- **API** public origin (TLS), e.g. `https://api.example.com`
- **Dashboard** (Next.js) public origin
- **Object storage** endpoint and bucket
- **PostgreSQL** DSN (from managed service or self-hosted)
- **Redis** URL if you add caching/queues later (Compose uses `REDIS_URL` today for local)
- **Widget script** host if served separately from the dashboard

## Redis

Local Compose exposes `REDIS_URL`. For staging/production, wire the same variable if your deployment uses Redis; otherwise omit until features require it.
