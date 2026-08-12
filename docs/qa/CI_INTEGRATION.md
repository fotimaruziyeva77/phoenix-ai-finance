# CI: PostgreSQL integration tests (GitHub Actions)

Jobs use **Python 3.12** (same as the API Docker image and `pyproject.toml`). The **Lint** job runs `scripts/check_python_version.py` so a misconfigured runner fails immediately.

Pull requests run **`pytest -m integration`** against a real **PostgreSQL 16** service container after **`alembic upgrade head`**. This gates merges on DB-backed flows (auth, leads, widget, Telegram APIs, RBAC, knowledge, MVP journey, etc.).

## Workflow

- File: `.github/workflows/ci.yml`
- Job: **Backend integration tests** (`backend-integration`)
- Command: `pytest tests -m integration` (override with env `PYTEST_INTEGRATION_ARGS` if you fork the workflow)

Redis is **not** required in CI: rate-limit integration tests use **fakeredis**.

## Deterministic environment variables

| Variable | CI value (typical) | Purpose |
| --- | --- | --- |
| `APP_ENVIRONMENT` | `local` | Avoids strict production Settings validation (caps, etc.). |
| `TEST_DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/botforge_ci` | Preferred URL for `tests/integration_db.py` (must be reachable from the runner). |
| `DATABASE_URL` | Same async URL for pytest step | `get_settings()` / engine creation when tests do not patch env. |
| `JWT_SECRET_KEY` | 32+ char non-secret placeholder | JWT signing in auth integration tests. |
| `GEMINI_API_KEY` | Non-empty placeholder | Satisfies Settings when modules load the app; LLM calls are mocked in tests. |

**Note:** On the GitHub runner, the Postgres service is published on **`127.0.0.1:5432`**. Do **not** use `@postgres:` in these URLs when testing from the job container with port mapping (see `tests/integration_db.py`).

## Migrations

The integration job runs **`alembic upgrade head`** once with a sync `DATABASE_URL` (`postgresql://...`) before pytest. Individual modules may still run upgrades in fixtures (idempotent `upgrade head`).

## Artifacts on failure

When the integration job fails, it uploads **`ci-artifacts/`** (JUnit XML, pytest log, coverage XML). Download from the workflow run’s **Artifacts** section.

## Required status check (branch protection)

In **GitHub → Settings → Branches → Branch protection rules** for `main` (and `master` if used):

1. Require status checks to pass before merging.
2. Add **`CI status gate`** (aggregate job) **or** individually require:
   - `Lint (Python)`
   - `Backend tests`
   - **`Backend integration tests`**
   - `Frontend (lint, test, build)`
   - `Embed widget (test, build)`
   - `Migration sanity (Alembic)`

Using **`CI status gate`** is recommended: it fails if **any** required job fails or is **skipped** (e.g. lint failure cascading to skipped downstream jobs).

## Local parity

Use **Python 3.12** (see repo `.python-version` and `python scripts/check_python_version.py`).

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://USER:PASS@127.0.0.1:5432/DBNAME"
export DATABASE_URL="$TEST_DATABASE_URL"
export JWT_SECRET_KEY="$(python -c 'print("x"*32)')"
export GEMINI_API_KEY="local-placeholder"
alembic upgrade head
python -m pytest tests -m integration -v
```

## Optional: faster curated subset

If the full integration matrix becomes too slow, set in a fork:

```yaml
env:
  PYTEST_INTEGRATION_ARGS: '-m "integration and not knowledge_processing"'
```

Re-evaluate coverage before weakening the gate.
