# Operations runbook: build, migrate, start, rollback

Assumptions: Linux or macOS shell, Docker available where noted, and secrets supplied via the environment (never committed).

## Build

### API container image

From the repository root:

```bash
./scripts/deploy/build_image.sh
```

Or explicitly:

```bash
docker build -t botforge-ai-api:local .
```

The image is **Python 3.12** (`python:3.12-slim-bookworm`), runs as UID 1000, exposes port 8000, and uses `CMD ["python", "main.py"]` (see `Dockerfile`).

### Frontend (dashboard)

```bash
cd frontend && npm ci && npm run build
```

Set `NEXT_PUBLIC_API_BASE_URL` (and any other `NEXT_PUBLIC_*`) for the **target tier** before `npm run build`.

### Embed widget

```bash
cd embed/widget && npm ci && npm run build
```

## Migrate

**Rule:** Take a **database backup** (snapshot or logical dump) before applying migrations in staging or production.

**Typical order:** Run migrations **before** switching traffic to application code that **depends** on the new schema. If the migration is backward-compatible, the **current** app version can keep running during `upgrade head`; then deploy the new containers. If it is not backward-compatible, plan a maintenance window or a blue/green cutover with both steps coordinated.

Run Alembic from the repo root with `DATABASE_URL` pointing at the target database (async URL is supported; `alembic/env.py` normalizes `postgresql://` to `postgresql+asyncpg://`):

```bash
./scripts/deploy/migrate.sh
```

Set `DATABASE_URL` or `APP_DATABASE_URL` in the process environment **without** putting the password on the shell command line when possible (shell history and CI logs). Prefer your platform’s secret injection, a short-lived credentials file readable only to the deploy user, or `docker run --env-file` with a file that is **not** committed.

Equivalent to the script:

```bash
alembic upgrade head
```

### Running migrations inside a container

If the API image is already built:

```bash
docker run --rm --env-file /secure/path/db.env botforge-ai-api:tag alembic upgrade head
```

Use a Docker **network** (or host networking) so `HOST` in the DSN resolves (managed DB hostname, not `localhost` from inside an isolated network namespace). Avoid `-e DATABASE_URL='...password...'` in shared terminals or logged CI steps where alternatives exist.

## Start

### Process supervisor / VM

Ensure strict-tier env vars are set (`APP_ENVIRONMENT=staging` or `production`, `APP_RELOAD=false`, etc.), then:

```bash
./scripts/deploy/start_backend.sh
```

This invokes `python main.py`, which runs Uvicorn with `host`/`port`/`reload` from `Settings`.

### Docker Compose (local stack)

```bash
docker compose up -d --build
```

### Production-oriented serving

For multiple workers behind a reverse proxy, a common pattern is **Gunicorn + Uvicorn workers**; that is **not** wired in this repository yet—add a `Procfile` or process command when you standardize on a host. Until then, document your platform’s recommended ASGI command and keep **one worker** if you rely on in-memory rate limits.

## Rollback-safe notes

### Application code

- **Docker Compose (staging):** if you deploy with `scripts/deploy/staging-deploy.sh`, run `scripts/deploy/rollback-staging.sh` to return to the image saved in `.deploy/staging-previous`, or `ROLLBACK_IMAGE=ghcr.io/.../api:<tag> ./scripts/deploy/rollback-staging.sh` for a pinned digest/tag. See [CI_CD_STAGING.md](./CI_CD_STAGING.md).
- **Blue/green or rolling:** deploy the **previous image tag** (or git SHA) your platform still has; no code rollback in the DB.
- **Kubernetes / ECS / Nomad:** keep at least one prior revision and switch traffic or scale.

### Database schema

- Alembic **downgrade** is only safe if the previous app version is compatible with the older schema:

  ```bash
  alembic downgrade -1
  ```

- Prefer **forward-fix** migrations for production when data has already been transformed.
- Always restore from **backup** if downgrade is unsafe or migration partially applied (platform-specific procedure).

### Object storage

- Rolling back code does not revert uploaded PDFs; bucket lifecycle/versioning is a separate operational choice.

### Telegram webhooks

- After API URL changes, reconnect or re-register webhooks so Telegram points at the correct host.

## Fast production diagnosis

Use this sequence to narrow incidents quickly. Details and alert hooks: [OBSERVABILITY.md](./OBSERVABILITY.md).

1. **Identify the release** — In Sentry (API + frontend projects), note **Release** on the issue. Match to the deployed image tag / `BOTFORGE_API_IMAGE` digest and the dashboard build’s `NEXT_PUBLIC_SENTRY_RELEASE`. GitHub Actions: `release-image.yml` sets `SENTRY_RELEASE=${{ github.ref_name }}@${{ github.sha }}`; staging build uses `staging@<sha>`.
2. **Get a correlation handle** — From a user report or browser devtools: copy **request id** (API JSON error, response header `X-Request-ID`, or support tooling). Dashboard calls send `X-Correlation-ID` per tab; search logs for `request_id` and `correlation_id` together.
3. **Search structured logs** — With JSON logging enabled, filter `request_id=<uuid>` to see the full request line (`http_request`, route, `http_status`, `duration_ms`). If the edge sent `traceparent`, also filter `w3c_trace_id=<32-char-hex>`.
4. **Classify the failure** — **5xx:** `observability_signal=api_server_error` or Sentry stack traces. **AI:** Sentry domain `ai_provider` or AI error codes in API responses. **Queue:** `knowledge_ingestion_metric` / `observability_signal=queue_dead_letter`. **Telegram:** `telegram_channel_event` with `observability_signal=telegram_failure` or `telegram_delivery_failure`.
5. **Spend / capacity** — For “cost” or “quota” suspicions, query `ai_usage_logs` (see OBSERVABILITY.md) for the affected time window and `bot_id` if known.
6. **Rollback** — If a single release regressed, roll back the API image (and redeploy the previous frontend build if needed) using the rollback notes above; keep Sentry release tags aligned so you can confirm the reverted version in new events.
