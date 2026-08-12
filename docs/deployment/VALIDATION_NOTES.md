# Deployment foundation — validation notes

Internal audit checklist for the deployment/release docs and scripts (repeat after major config or Dockerfile changes).

## 1. Environment separation

| Check | Status |
|-------|--------|
| Tiers **local**, **docker**, **staging**, **production**/`prod` are named and scoped | See [ENVIRONMENTS.md](./ENVIRONMENTS.md) |
| **Strict** validation applies only to `staging`, `production`, `prod` (`app/core/config.py`: `_STRICT_DEPLOY_ENVIRONMENTS`) | Code + ENVIRONMENTS.md aligned |
| **docker** Compose remains non-strict (local parity, not a hosted tier) | Documented |

## 2. Required environment variables

| Check | Status |
|-------|--------|
| Strict-tier **startup** requirements listed | [PRODUCTION_ENV.md](./PRODUCTION_ENV.md) § Core API |
| Feature-specific vars (OAuth, S3, Gemini, Telegram) separated from core | Same doc, tables use **F** |
| Aliases (`DATABASE_URL` vs `APP_DATABASE_URL`, etc.) documented | PRODUCTION_ENV + config `Field` descriptions |

**Clarification:** For strict tiers, `APP_RELOAD`, `APP_LOG_REQUEST_BODY`, and `APP_EXPOSE_ERROR_DETAILS` are marked **D** in [PRODUCTION_ENV.md](./PRODUCTION_ENV.md): defaults satisfy validation when omitted; unsafe explicit values still fail.

## 3. Deployment / build scripts

| Script | Purpose | Coherence |
|--------|---------|-----------|
| `scripts/deploy/build_image.sh` | `docker build` from repo root | Matches [RUNBOOK.md](./RUNBOOK.md); default tag `botforge-ai-api:local` |
| `scripts/deploy/migrate.sh` | `alembic upgrade head` | Requires `DATABASE_URL` or `APP_DATABASE_URL`; does not echo secrets |
| `scripts/deploy/start_backend.sh` | `python main.py` | Uvicorn settings from env; strict tiers need full env (or `.env` on disk — avoid committing) |

Scripts assume **Bash** and run from paths relative to repo root after `cd` inside the script.

## 4. Migration step

| Check | Status |
|-------|--------|
| Runbook documents `migrate.sh` and raw `alembic upgrade head` | [RUNBOOK.md](./RUNBOOK.md) § Migrate |
| Backup-before-migrate called out for staging/production | RUNBOOK + [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) |
| In-container migration pattern documented | RUNBOOK (with network / secret hygiene notes) |
| CI runs migration sanity | `.github/workflows/ci.yml` `migrations` job |

## 5. Rollback-safe guidance

| Check | Status |
|-------|--------|
| App rollback = previous image / revision | RUNBOOK § Rollback-safe notes |
| DB rollback = downgrade only when schema-compatible; prefer forward-fix + backup restore | RUNBOOK + RELEASE_PROCESS § Emergency rollback |
| Object storage and Telegram caveats | RUNBOOK |

## 6. Staging workflow skeleton

| Check | Status |
|-------|--------|
| `deploy-staging.yml` performs a **real** Docker build (`push: false`) | No fake deploy steps |
| Extension points documented | [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) |

---

**Gaps (intentional):** no TLS/DNS automation, no secret rotation, no multi-worker ASGI command in-repo — listed in RELEASE_PROCESS § 5.
