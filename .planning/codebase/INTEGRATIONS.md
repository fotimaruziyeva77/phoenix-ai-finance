# External Integrations

**Analysis Date:** 2026-05-30

## APIs & External Services

**AI / LLM:**
- Google Gemini (Generative Language API) - Chat completions, intent classification, sales orchestration
  - SDK/Client: `httpx` (direct HTTP, no Python SDK)
  - Implementation: `app/integrations/providers/gemini.py` (re-exported via `app/ai_providers/gemini.py`)
  - Auth: `GEMINI_API_KEY` / `APP_GEMINI_API_KEY` (sent as `x-goog-api-key` header, not query param)
  - Base URL: `https://generativelanguage.googleapis.com/v1beta` (configurable via `GEMINI_API_BASE_URL`)
  - Default model: `gemini-2.5-flash` (configurable via `GEMINI_DEFAULT_MODEL`)
  - Features: 429 retry with exponential backoff + `Retry-After` header honoring, thinking config support for Gemini 2.5+

- Google Gemini Text Embeddings - Semantic cache similarity matching
  - SDK/Client: `httpx` (direct HTTP)
  - Implementation: `app/integrations/gemini_text_embedding.py`
  - Auth: `GEMINI_API_KEY` (same key as completions)
  - Endpoint: `https://generativelanguage.googleapis.com/v1/models/{model}:embedContent`
  - Default model: `models/text-embedding-004` (configurable via `EMBEDDING_MODEL`)

**Payments:**
- Stripe - Subscription billing, checkout, customer portal, webhooks
  - SDK/Client: `stripe>=7.0.0`
  - Implementation: `app/services/billing_service.py`, endpoint handler `app/api/v1/billing.py`
  - Auth: `STRIPE_SECRET_KEY` / `APP_STRIPE_SECRET_KEY` (server-side only)
  - Webhook validation: `STRIPE_WEBHOOK_SECRET` / `APP_STRIPE_WEBHOOK_SECRET` (signature verification)
  - Publishable key: `STRIPE_PUBLISHABLE_KEY` (exposed to frontend)
  - Plans: `starter`, `pro`, `business`, `enterprise` with per-plan Price IDs (`STRIPE_PRICE_ID_STARTER`, etc.)

**Email Delivery:**
- Resend.com - Transactional emails (verification, password reset)
  - SDK/Client: `resend>=2.0.0` (synchronous SDK wrapped in thread pool)
  - Implementation: `app/integrations/email/resend_client.py`, `app/integrations/email/templates.py`
  - Auth: `RESEND_API_KEY` / `APP_RESEND_API_KEY`
  - Fail-open: email errors are logged but never raise to callers
  - From address: `APP_EMAIL_FROM_ADDRESS` (default: `noreply@botforge.ai`)

**Messaging / Bots:**
- Telegram Bot API - Outbound bot replies and webhook registration
  - SDK/Client: `httpx` (direct HTTP)
  - Implementation: `app/integrations/telegram_bot_api/client.py` (`TelegramBotApiClient`)
  - Auth: Per-bot token (stored encrypted with Fernet at rest in DB, decrypted on use)
  - Base URL: `https://api.telegram.org`
  - Lead alerts: separate `TELEGRAM_LEAD_ALERT_BOT_TOKEN` / `APP_TELEGRAM_LEAD_ALERT_BOT_TOKEN`
  - Chat ID for alerts: `TELEGRAM_LEAD_ALERT_CHAT_ID` / `APP_TELEGRAM_LEAD_ALERT_CHAT_ID`
  - Webhook registration helper: `app/integrations/telegram_webhook_registration.py`
  - Reply formatting: `app/integrations/telegram_reply_format.py`
  - Bot reply service: `app/integrations/telegram_bot_reply.py`

**Error Tracking:**
- Sentry - Unhandled exceptions, AI provider failures, server-mapped 5xx errors
  - SDK/Client: `sentry-sdk>=2.0.0` (optional; no-op when absent)
  - Implementation: `app/core/error_tracking.py`
  - Auth: `SENTRY_DSN` / `APP_SENTRY_DSN`
  - Default integrations disabled (manual capture only to prevent PII leakage)
  - Sensitive keys scrubbed before sending (passwords, tokens, cookies, headers)

## Data Storage

**Databases:**
- PostgreSQL (async)
  - Connection: `DATABASE_URL` or `APP_DATABASE_URL` (format: `postgresql+asyncpg://user:pass@host:port/dbname`)
  - Client: SQLAlchemy 2.0 async ORM with asyncpg driver (`app/core/db.py`)
  - Session factory: `async_sessionmaker` with `expire_on_commit=False`, `autoflush=False`
  - Migrations: Alembic (`alembic/versions/`, `alembic.ini`)
  - All models in `app/models/`: `User`, `Bot`, `Subscription`, `Lead`, `KnowledgeFile`, `KnowledgeChunk`, `TelegramConfig`, `WidgetConfig`, `ConversationFlow`, `RefreshSession`, `AuditLog`, `WebhookLog`, `FeatureFlag`, `Coupon`, `EmailCampaign`, `SupportTicket`

**Caching:**
- Redis (optional, strongly recommended in production)
  - Connection: `REDIS_URL` / `RATE_LIMIT_REDIS_URL` / `APP_REDIS_URL` (several aliases)
  - Client: `redis.asyncio` (`app/core/redis_client.py`, singleton per process)
  - Uses:
    - Sliding-window rate limiting (`app/core/limiters/redis_sliding_window.py`)
    - Public widget abuse tracking (`app/core/widget_abuse_redis.py`)
    - Semantic completion cache (`app/services/semantic_completion_cache.py`; optional separate URL: `AI_SEMANTIC_CACHE_REDIS_URL`)
    - Exact completion cache (`app/services/ai_completion_cache.py`; key prefix `bf:ai:ec`)
    - Knowledge ingestion queue (`app/core/knowledge_ingestion_queue.py`; BRPOP/LPUSH list)
    - Sales LLM burst limiter (`app/services/sales_llm_burst_limiter.py`)
  - Key prefixes: `bf:rl` (rate limits), `bf:ai:sc` (semantic cache), `bf:ai:ec` (exact cache), `bf:ai:llmburst` (burst), `bf:knowledge:ingestion` (queue)
  - Fallback: in-process `InMemorySlidingWindowLimiter` when Redis URL is unset

**File Storage:**
- S3-compatible object storage (AWS S3 or MinIO)
  - SDK/Client: `boto3>=1.35.0` (synchronous, run in thread pool)
  - Implementation: `app/integrations/storage/s3.py` (`S3CompatibleObjectStorage`)
  - Credentials: `AWS_ACCESS_KEY_ID` / `APP_OBJECT_STORAGE_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` / `APP_OBJECT_STORAGE_SECRET_ACCESS_KEY`
  - Bucket: `S3_BUCKET` / `APP_OBJECT_STORAGE_BUCKET`
  - Endpoint: `S3_ENDPOINT_URL` / `APP_S3_ENDPOINT_URL` / `MINIO_ENDPOINT` (set for MinIO/custom S3)
  - Region: `AWS_REGION` / `APP_OBJECT_STORAGE_REGION` (default: `us-east-1`)
  - Addressing style: `path` (default, for MinIO) or `virtual` (standard AWS S3)
  - Purpose: storing uploaded knowledge PDF files (`app/services/bot_knowledge_file_service.py`)
  - Base class: `app/integrations/storage/base.py` (`ObjectStorageBackend`)

## Authentication & Identity

**Custom Auth (primary):**
- Email + password signup/login with JWT tokens
  - Password hashing: Argon2id (`app/core/security/passwords.py`, `argon2-cffi`)
  - Tokens: JWTs signed with HMAC (`PyJWT`); access token 15 min, refresh token 7 days (configurable)
  - JWT secret: `JWT_SECRET_KEY` / `APP_JWT_SECRET_KEY` (min 32 chars; required in production)
  - Refresh session persistence: `app/models/refresh_session.py` table with hashed token
  - Cookie auth mode: optional HttpOnly cookie + CSRF token (`AUTH_COOKIE_ENABLED`)
  - Implementation: `app/core/security/jwt_tokens.py`, `app/services/auth_service.py`

**OAuth Providers:**
- Google OAuth 2.0 (authorization code flow)
  - Implementation: `app/integrations/google_idp.py`
  - Endpoints: `https://accounts.google.com/o/oauth2/v2/auth`, `https://oauth2.googleapis.com/token`, `https://www.googleapis.com/oauth2/v3/userinfo`
  - Credentials: `GOOGLE_CLIENT_ID` / `APP_GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` / `APP_GOOGLE_OAUTH_CLIENT_SECRET`
  - Redirect URI: `GOOGLE_OAUTH_REDIRECT_URI` / `APP_GOOGLE_OAUTH_REDIRECT_URI`
  - API route handler: `app/api/v1/google_oauth.py`

- GitHub OAuth (authorization code + user/email API)
  - Implementation: `app/integrations/github_idp.py`
  - Endpoints: `https://github.com/login/oauth/authorize`, `https://github.com/login/oauth/access_token`, `https://api.github.com/user`, `https://api.github.com/user/emails`
  - Credentials: `GITHUB_CLIENT_ID` / `APP_GITHUB_OAUTH_CLIENT_ID`, `GITHUB_CLIENT_SECRET` / `APP_GITHUB_OAUTH_CLIENT_SECRET`
  - Redirect URI: `GITHUB_OAUTH_REDIRECT_URI` / `APP_GITHUB_OAUTH_REDIRECT_URI`
  - API route handler: `app/api/v1/github_oauth.py`

- OAuth exchange token flow: `app/integrations/oauth_exchange_store.py`, `app/api/v1/oauth_exchange.py`

**RBAC:**
- Two roles: `customer_admin` (default tenant) and `superadmin` (platform operator)
- Implementation: `app/core/rbac.py`, role stored on `User` model (`app/models/enums.py`)

## Monitoring & Observability

**Error Tracking:**
- Sentry (see above) — configured at startup, active only when `SENTRY_DSN` is set

**Logs:**
- `structlog>=24.4.0` with stdlib backend (`app/core/logging.py`)
- Format: JSON (`APP_LOG_JSON=true`) or colored console (development)
- All requests logged via `RequestLoggingMiddleware` (`app/core/middleware.py`)
- Log level: `APP_LOG_LEVEL` (default `INFO`)
- Sensitive fields never logged (no request bodies in staging/production)

## CI/CD & Deployment

**Hosting:**
- Docker container (single process, non-root `app` user, port 8000)
- Docker Compose for local stack (`docker-compose.yml`)
- Scripts: `scripts/verify_stack.py`, `scripts/verify_docker.sh`, `scripts/verify_docker.ps1`

**CI Pipeline:**
- Not detected in repository (no `.github/workflows/` present under scanned paths; CI referenced in comments but workflow files not present)

## Webhooks & Callbacks

**Incoming:**
- Telegram Bot API webhooks: `POST /api/v1/public/telegram/{bot_id}/webhook`
  - Handler: `app/api/v1/public_telegram.py`
  - Validation: `X-Telegram-Bot-Api-Secret-Token` header matched against stored secret
  - Max body: 512 KB
  - Processing: `app/services/telegram_webhook_inbound_service.py`

- Stripe billing webhooks: `POST /api/v1/billing/webhook` (inferred from billing router structure)
  - Handler: `app/api/v1/billing.py`
  - Validation: Stripe webhook signature using `STRIPE_WEBHOOK_SECRET`
  - Events logged to `webhook_log` table via `app/repositories/webhook_log_repository.py`

**Outgoing:**
- Telegram Bot API calls: `sendMessage`, `setWebhook` etc. via `TelegramBotApiClient`
  - From: `app/integrations/telegram_bot_api/client.py`

- Resend.com email sends: verification emails, password reset emails
  - From: `app/integrations/email/resend_client.py`

- Stripe API calls: checkout session creation, customer portal, subscription management
  - From: `app/services/billing_service.py`

- Gemini API calls: chat completions, text embeddings
  - From: `app/integrations/providers/gemini.py`, `app/integrations/gemini_text_embedding.py`

- Google / GitHub OAuth token exchange calls (outgoing during callback)
  - From: `app/integrations/google_idp.py`, `app/integrations/github_idp.py`

## Environment Configuration

**Required in production (validated at startup):**
- `DATABASE_URL` or `APP_DATABASE_URL`
- `JWT_SECRET_KEY` or `APP_JWT_SECRET_KEY` (min 32 chars)
- `APP_TELEGRAM_TOKEN_FERNET_KEY` (valid Fernet key)
- `APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT` (> 0)
- `APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER` (> 0)

**Optional but needed for features:**
- `REDIS_URL` — rate limiting, caches, knowledge ingestion queue
- `GEMINI_API_KEY` — all AI features
- `SENTRY_DSN` — error tracking
- `RESEND_API_KEY` — email delivery
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` — billing
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Google OAuth
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` — GitHub OAuth
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` — file storage
- `PUBLIC_API_BASE_URL` — Telegram webhook registration

**Secrets location:**
- `.env` file at project root (loaded by `pydantic-settings`; never committed)
- At-rest Telegram bot tokens: Fernet-encrypted in the `telegram_configs` database table

---

*Integration audit: 2026-05-30*
