# Technology Stack

**Analysis Date:** 2026-05-30

## Languages

**Primary:**
- Python 3.12 - All application code, services, API, workers, migrations

**Secondary:**
- None detected (pure Python backend; frontend is a separate directory not analyzed)

## Runtime

**Environment:**
- Python 3.12.x (pinned via `Dockerfile`, `.python-version`, enforced by `scripts/check_python_version.py`)
- ASGI process via Uvicorn (standard extras)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (flat pinned-range file, no lock file like `poetry.lock`)

## Frameworks

**Core:**
- FastAPI `>=0.115.0` - REST API framework, all routes under `app/api/`
- Pydantic v2 (via `pydantic-settings>=2.6.0`) - Settings, request/response schemas
- Starlette - CORS, middleware (used directly via `starlette.middleware.cors.CORSMiddleware`)
- Uvicorn `>=0.32.0` (standard extras) - ASGI server

**ORM / Database:**
- SQLAlchemy `>=2.0.36` (asyncio extra) - Async ORM, all models in `app/models/`
- asyncpg `>=0.30.0` - Async PostgreSQL driver
- Alembic `>=1.14.0` - Database migrations (`alembic/` directory, `alembic.ini`)

**Testing:**
- pytest `>=8.0.0` - Test runner (`pytest.ini`, tests in `tests/`)
- pytest-asyncio `>=0.24.0` - Async test support (`asyncio_mode = auto`)
- fakeredis `>=2.23.0` (lua extra) - In-process Redis mock for unit tests

**Build/Dev:**
- Ruff - Linting and formatting (configured in `pyproject.toml`)
- Docker - Container runtime (`Dockerfile`, `docker-compose.yml`)

## Key Dependencies

**Critical:**
- `httpx>=0.27.0` - Async HTTP client for all outbound API calls (Gemini, Telegram, Google OAuth, GitHub OAuth)
- `redis>=5.0.0` - Async Redis client (`redis.asyncio`) for rate limiting, caching queues, semantic cache
- `cryptography>=42.0.0` - Fernet symmetric encryption for Telegram bot tokens at rest
- `PyJWT>=2.9.0` - JWT access and refresh token signing/verification (HMAC HS256/384/512)
- `argon2-cffi>=23.1.0` - Argon2id password hashing (`app/core/security/passwords.py`)
- `pypdf>=5.0.0` - PDF text extraction for knowledge file ingestion pipeline

**Infrastructure:**
- `boto3>=1.35.0` - S3-compatible object storage client for knowledge file uploads (`app/integrations/storage/s3.py`)
- `resend>=2.0.0` - Transactional email delivery (`app/integrations/email/resend_client.py`)
- `stripe>=7.0.0` - Stripe billing SDK for subscription checkout/portal/webhooks (`app/services/billing_service.py`)
- `sentry-sdk>=2.0.0` - Error tracking (optional, initialized at startup if DSN set; `app/core/error_tracking.py`)
- `structlog>=24.4.0` - Structured logging with JSON or console rendering (`app/core/logging.py`)
- `python-multipart>=0.0.9` - Multipart form parsing for file uploads
- `email-validator>=2.0.0` - Email address validation for auth endpoints

## Configuration

**Environment:**
- All settings loaded from `.env` file and environment variables via `pydantic-settings`
- Env var prefix: `APP_` (e.g., `APP_DATABASE_URL`, `APP_JWT_SECRET_KEY`)
- Many fields accept multiple alias names (e.g., `DATABASE_URL` or `APP_DATABASE_URL`)
- Settings class: `app/core/config.py` → `Settings` (cached singleton via `lru_cache`)
- Strict environment validation: `staging` and `production` environments enforce required fields (DATABASE_URL, JWT_SECRET_KEY, TELEGRAM_TOKEN_FERNET_KEY, non-zero AI token caps)

**Key config groups (all in `app/core/config.py`):**
- Server: `APP_HOST`, `APP_PORT`, `APP_RELOAD`, `APP_ENVIRONMENT`
- Logging: `APP_LOG_LEVEL`, `APP_LOG_JSON`
- Database: `DATABASE_URL` or `APP_DATABASE_URL` (PostgreSQL asyncpg URL)
- Redis: `REDIS_URL` or `RATE_LIMIT_REDIS_URL` (optional; falls back to in-memory)
- JWT: `JWT_SECRET_KEY`, `APP_JWT_ALGORITHM` (HS256/384/512), token lifetimes
- Auth cookies: `AUTH_COOKIE_ENABLED`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`
- CORS: `APP_CORS_ORIGINS` (comma-separated list), `APP_CORS_ALLOW_CREDENTIALS`
- Sentry: `SENTRY_DSN` or `APP_SENTRY_DSN`
- AI / Gemini: `GEMINI_API_KEY`, `GEMINI_DEFAULT_MODEL`, `GEMINI_API_BASE_URL`
- Semantic/exact cache: `AI_SEMANTIC_CACHE_ENABLED`, `AI_EXACT_CACHE_ENABLED`
- S3 / object storage: `S3_ENDPOINT_URL`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Email: `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, per-plan price IDs
- Telegram: `TELEGRAM_TOKEN_FERNET_KEY`, `PUBLIC_API_BASE_URL`
- OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

**Build:**
- `Dockerfile` — `python:3.12-slim-bookworm` base image, installs `requirements.txt`, exposes port 8000
- `docker-compose.yml` — local stack orchestration
- Build args: `APP_VERSION`, `SENTRY_RELEASE` (injected by CI)
- `pyproject.toml` — Ruff linter/formatter config (target Python 3.12, line length 120, double quotes)

## Platform Requirements

**Development:**
- Python 3.12.x exactly
- PostgreSQL (required for integration tests; `TEST_DATABASE_URL` or `DATABASE_URL`)
- Redis (optional for local; required for distributed rate limiting, semantic cache, knowledge ingestion queue)
- S3-compatible storage (optional; local filesystem not used — object storage disabled when unconfigured)

**Production:**
- Docker container (single process via `CMD ["python", "main.py"]`)
- PostgreSQL (required; `DATABASE_URL` enforced in staging/production)
- Redis (strongly recommended; falls back to in-process limiters which are not safe across workers)
- S3 or S3-compatible endpoint (MinIO supported via `S3_ENDPOINT_URL` path style)
- Sentry DSN (optional, recommended for production error tracking)
- Deployment tier inferred from `APP_ENVIRONMENT` (`local`, `docker`, `staging`, `production`)

---

*Stack analysis: 2026-05-30*
