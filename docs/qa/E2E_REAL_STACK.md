# Real-stack E2E (Playwright)

End-to-end tests under `frontend/e2e/real-stack/` drive the **real** Next.js app, which rewrites `/api/*` to FastAPI (`BACKEND_INTERNAL_URL`, default `http://127.0.0.1:8000`). **No route mocking** is used in these specs.

## Environment strategy

| Layer | Responsibility |
|--------|------------------|
| **PostgreSQL** | Dedicated DB (or schema) for E2E; migrations via `alembic upgrade head`. |
| **FastAPI** | `uvicorn app.main:app` with `DATABASE_URL`, `JWT_SECRET_KEY`, and (optional) object storage + `GEMINI_API_KEY` for AI-backed widget chat. |
| **Next.js** | `npm run dev` with `BACKEND_INTERNAL_URL` pointing at the API; `NEXT_PUBLIC_API_BASE_URL` empty so the browser uses same-origin `/api/...`. |
| **Playwright** | `frontend/playwright.real-stack.config.ts` starts Next by default; set `E2E_SKIP_WEBSERVER=1` when Next is already running (e.g. Docker Compose). |

### Isolation & reset

1. **Onboarding spec** (`onboarding.spec.ts`) uses a **unique email per run** and clears `localStorage` keys for auth + create-bot draft.
2. **Seeded spec** (`seeded-workspace.spec.ts`) expects `frontend/e2e/real-stack/seed-output.json` from `scripts/seed_e2e_stack.py`, which **deletes and recreates** the seed user by email (`E2E_SEED_EMAIL`, default `e2e-stack@botforge.test`).

### Optional toggles

| Variable | Effect |
|----------|--------|
| `E2E_WITH_OBJECT_STORAGE=1` | Run PDF upload against real S3-compatible storage (requires `S3_*` / object storage env on the API). |
| `E2E_WIDGET_CHAT=1` | After bootstrap, POST public widget chat (requires working AI config on the **API** process). |
| `E2E_TELEGRAM_BOT_TOKEN` | If set (length ≥ 10), seeded suite calls `POST .../telegram/token/validate` (no persistence). |
| `E2E_SEED_OUTPUT_PATH` | Override path to seed JSON (default: `frontend/e2e/real-stack/seed-output.json`). |

## Local run

Use **Python 3.12** for the API (same as CI and `Dockerfile`); run `python scripts/check_python_version.py` to confirm.

From repository root (terminal 1):

```bash
# PostgreSQL running; DATABASE_URL async (postgresql+asyncpg://...)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/botforge_e2e
export JWT_SECRET_KEY=your-32-char-minimum-secret-for-local
alembic upgrade head
python scripts/seed_e2e_stack.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/` (terminal 2):

```bash
npm ci
npx playwright install chromium
npm run test:e2e:real
```

Artifacts on failure: `frontend/test-results/real-stack/` (screenshots, traces, video per `playwright.real-stack.config.ts`).

## CI / nightly

See `.github/workflows/e2e-real-stack.yml` (manual `workflow_dispatch` and optional schedule). It does **not** gate the default PR CI; run it on staging or nightly when Postgres + API + Next are available.

**Staging pipeline:** mirror the same steps—migrate → seed → start API → `npm run test:e2e:real` with `CI=true`. Upload `test-results/real-stack` and `playwright-report` as artifacts on failure.

## Covered journeys

| Journey | Spec | Notes |
|---------|------|--------|
| Signup / login | `onboarding.spec.ts` | Register + second test login. |
| Create bot | `onboarding.spec.ts` | Full wizard against real `POST /api/v1/bots`. |
| Knowledge upload | `onboarding.spec.ts` | Gated by `E2E_WITH_OBJECT_STORAGE=1`. |
| Widget | `onboarding.spec.ts` + `seeded-workspace.spec.ts` | Bootstrap GET; chat POST only if `E2E_WIDGET_CHAT=1`. |
| Leads dashboard | `seeded-workspace.spec.ts` | Seeded lead row. |
| Telegram (dry validate) | `seeded-workspace.spec.ts` | Optional `E2E_TELEGRAM_BOT_TOKEN`. |
| Dashboard verification | `seeded-workspace.spec.ts` | Bots + leads links. |
