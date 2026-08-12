# Environment separation

## Python runtime

**Python 3.12** is the only supported interpreter for the backend: see the repo root **`README.md`**, **`.python-version`**, **`pyproject.toml`** (Ruff `target-version`), and the **`Dockerfile`**. CI fails fast if the job interpreter is not 3.12.x (`scripts/check_python_version.py`).

Configuration is loaded from the process environment and optional `.env` (see `app.core.config.Settings`: prefix `APP_`, plus documented unprefixed aliases such as `DATABASE_URL` and `JWT_SECRET_KEY`).

## Canonical tiers

| Tier | Typical `APP_ENVIRONMENT` | Purpose |
|------|---------------------------|---------|
| **Local** | `local` | Developer laptop; uvicorn may use `APP_RELOAD=true`; Postgres/Redis/MinIO optional or ad hoc |
| **Docker (local stack)** | `docker` | Same codebase via `docker-compose.yml`; service DNS names (`postgres`, `minio`, …); **not** subject to strict deploy validation |
| **Staging** | `staging` | Pre-production: real TLS URLs, isolated DB and buckets, **same safety rules as production** in code |
| **Production** | `production` or `prod` | Live users; strict validation |

## Strict deploy validation (`staging`, `production`, `prod`)

For these values, `Settings` enforces:

- `DATABASE_URL` (or `APP_DATABASE_URL`) is set
- `APP_RELOAD` is false
- `APP_LOG_REQUEST_BODY` is false
- `APP_EXPOSE_ERROR_DETAILS` is false
- `JWT_SECRET_KEY` (or `APP_JWT_SECRET_KEY`) is set and at least 32 characters

This keeps staging behaviour aligned with production so issues surface before go-live.

## Config separation (future-safe)

1. **One set of variable names** across tiers; differ only **values** and **secrets** per environment (12‑factor style).
2. **Never commit** real `.env` files; use platform secret stores (GitHub Environments, Doppler, Vault, cloud parameter store, etc.).
3. **Separate infrastructure** for staging vs production: databases, object storage buckets, OAuth client IDs (or redirect URIs), Telegram webhooks, and Sentry projects.
4. **Optional** GitHub (or other) **Environment** named `staging` with its own secrets and protection rules; mirror for `production`.

## Frontend and embed

- **Frontend** (`frontend/`): `NEXT_PUBLIC_API_BASE_URL` must point at the API origin for that tier (e.g. `https://api.staging.example.com`). Build-time public vars are embedded in the bundle — use a distinct build per tier.
- **Embed widget** (`embed/widget/`): the bundle calls the API using the **`apiBaseUrl` passed at runtime** from the host page (see widget init options), not a baked-in production URL. Host the built script from your CDN or app origin per environment; only add `VITE_*` build-time variables if you introduce them in code.
