# Deployment foundation

Operational entry points for BotForge AI: environment model, production configuration, day‑two runbook, and release flow.

**Backend runtime:** Python **3.12** only (Dockerfile, CI, `pyproject.toml` / `.python-version`); see the repo root `README.md`.

**MVP launch (checklist, architecture verdict, env/migration/troubleshooting):** see **[docs/release/](../release/README.md)**.

| Document | Purpose |
|----------|---------|
| [ENVIRONMENTS.md](./ENVIRONMENTS.md) | **local**, **staging**, **production** (and **docker** Compose) — what each tier means and how `APP_ENVIRONMENT` behaves |
| [PRODUCTION_ENV.md](./PRODUCTION_ENV.md) | Secrets, public URLs, and provider/object-storage settings for staged and live deploys |
| [RUNBOOK.md](./RUNBOOK.md) | Build, migrate, start, and rollback-safe notes |
| [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) | Recommended promotion path staging → production and CI gates |
| [CI_CD_STAGING.md](./CI_CD_STAGING.md) | **Staging automation**: GHCR push, optional SSH Compose rollout, health checks, secrets/variables |
| [VERSIONING_AND_TAGS.md](./VERSIONING_AND_TAGS.md) | Semver git tags, image tags (`:staging`, `:sha`, `v*`), rollback references |
| [VALIDATION_NOTES.md](./VALIDATION_NOTES.md) | Checklist used to verify this deployment foundation |

Scripts (run on a host with Bash; paths are repo-relative):

- `scripts/deploy/build_image.sh` — build the API container image
- `scripts/deploy/staging-deploy.sh` — pull `BOTFORGE_API_IMAGE` and restart **backend** + **knowledge-worker** via Compose (records `.deploy/` for rollback)
- `scripts/deploy/rollback-staging.sh` — roll back to the previous recorded image (or `ROLLBACK_IMAGE=...`)
- `scripts/deploy/migrate.sh` — run Alembic against `DATABASE_URL`
- `scripts/deploy/start_backend.sh` — start the API process (same as `python main.py` with env-driven settings)

GitHub Actions:

- `.github/workflows/ci.yml` — lint, unit tests, **backend integration tests** (Postgres service + Alembic + `pytest -m integration`), frontend/widget, migrations, **CI status gate**; see [docs/qa/CI_INTEGRATION.md](../qa/CI_INTEGRATION.md).
- `.github/workflows/deploy-staging.yml` — build + **push API image to GHCR** (`:staging`, `:<sha>`), optional **SSH** `docker compose pull/up`, optional **`/api/v1/health`** verification; see [CI_CD_STAGING.md](./CI_CD_STAGING.md).
- `.github/workflows/release-image.yml` — on git tag `v*`, push semver + SHA tags to GHCR (no deploy).
