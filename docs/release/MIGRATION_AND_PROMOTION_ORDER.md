# Migration and release promotion order

Aligns application deploys with **Alembic** schema changes. Full narrative: [RUNBOOK.md](../deployment/RUNBOOK.md) § Migrate; release flow: [RELEASE_PROCESS.md](../deployment/RELEASE_PROCESS.md).

## Golden rules

1. **Backup first** (staging/production) — snapshot or logical dump before `alembic upgrade head`.
2. Prefer **backward-compatible migrations** so old app binaries can run during rollout; then deploy new code.
3. If a migration is **not** backward-compatible, plan a **maintenance window** or coordinated blue/green cutover: migrate and switch traffic in one controlled sequence.

## Recommended order (typical release)

| Step | Action |
|------|--------|
| 1 | CI green on the **exact commit** (or image digest) you will promote. |
| 2 | **Build** artifacts: API image, Next.js build (tier env vars), widget bundle. |
| 3 | **Backup** target database. |
| 4 | Run **`alembic upgrade head`** against target DB (from host or one-off container with `DATABASE_URL`). |
| 5 | **Deploy** new API (and frontend/widget) to route traffic to code that expects the new schema. |
| 6 | **Smoke test** health, auth, one critical path ([MVP_RELEASE_CHECKLIST.md](./MVP_RELEASE_CHECKLIST.md)). |
| 7 | **Telegram:** if API public URL changed, re-register or verify webhook. |

## When to migrate before vs with deploy

- **Before:** New code **requires** new columns/tables — migrate first, then roll app (if migration is compatible with old code) **or** migrate immediately before cutover in a short window.
- **After (rare):** Only if migration is a no-op for old code and you have a strong reason; still document the sequence per environment.

## Rollback

- **Application:** Redeploy previous image — no automatic DB rollback.
- **Database:** `alembic downgrade -1` only if the **previous** app version is compatible with the older schema; otherwise **restore from backup** or ship a **forward-fix** migration.

## Compose / local

`docker compose up` brings DB + services; run migrations once against the Compose Postgres URL (from host: published port, not `@postgres:`). Integration tests on the host need `TEST_DATABASE_URL` or `127.0.0.1` DSN.

## CI

`.github/workflows/ci.yml` **migrations** job applies `alembic upgrade head` against ephemeral Postgres — validates migration scripts apply cleanly; it does not replace staging/prod backup discipline.
