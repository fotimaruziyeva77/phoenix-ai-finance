# MVP end-to-end verification (BotForge AI)

This document maps **product-critical paths** to automated checks and calls out what still needs a **live channel** or **manual** validation.

## Layering

| Layer | Scope | When to run |
| --- | --- | --- |
| **A — API integration (pytest)** | Real PostgreSQL, HTTP via `TestClient`, same app code paths as production | **CI:** `.github/workflows/ci.yml` runs `pytest -m integration`. Local: `pytest tests/test_mvp_product_journey_integration.py -m integration` (+ DB URL) |
| **B — Focused integration** | Deeper coverage per feature (widget abuse, moderation, leads, Telegram logic) | Existing `tests/test_*_integration.py` modules |
| **C — Browser (Playwright)** | Next.js UI + real backend (or Next rewrites to FastAPI) | `cd frontend && E2E_REAL_BACKEND=1 npm run test:e2e -- e2e/mvp-landing-signup-dashboard-real.spec.ts` |
| **D — Manual / staging** | Long sales transcripts, real Telegram bot token, production observability stacks | Release checklist |

## Flow coverage matrix

| # | Flow | Primary automation | Notes |
| --- | --- | --- | --- |
| 1 | Landing → signup/login → dashboard | **C:** `mvp-landing-signup-dashboard-real.spec.ts`; **B:** `auth-flow.spec.ts` (mocked API UI only) | Real path needs FastAPI reachable from Next (`BACKEND_INTERNAL_URL` / default `127.0.0.1:8000` or `NEXT_PUBLIC_API_BASE_URL`). |
| 2 | Create bot → configure widget | **B:** `create-bot-wizard-real-flow.spec.ts` (wizard + list); **A:** `test_mvp_*` creates bot + `PATCH` widget | Widget wizard channel step is in Playwright real-flow spec. |
| 3 | Upload knowledge PDF | **A:** `test_mvp_product_journey_integration.py` (multipart + mocked object storage, same as `test_bot_knowledge_files_api_integration.py`) | Full extraction/RAG pipeline: `test_knowledge_file_processing_integration.py`, `test_ai_knowledge_chat_integration.py`. |
| 4 | Test AI in admin chat | **A:** `POST /api/v1/bots/{id}/chat/test` with injected provider; **B:** `test_bot_chat_api_integration.py` | LLM is **stubbed** in tests for determinism; set `E2E_REAL_GEMINI=1` only in a controlled env if you intentionally want live Gemini. |
| 5 | Widget visitor chat → **lead** | **B:** `test_public_widget_chat_api_integration.py` (conversation); **B:** `test_sales_lead_capture_flow_integration.py`, `test_telegram_lead_capture_integration.py` (orchestrator rules) | **End-to-end lead row** needs a **sales** bot, **closing/completed** funnel, niche fields + **phone** (`lead_creation_service`). Automating a full multi-turn sales dialog is brittle; validate on staging with scripted visitor or manual QA. |
| 6 | Telegram → **lead** | **B:** `test_telegram_lead_capture_integration.py` | Needs real BotFather token + webhook or tunnel for true E2E; keep integration tests as the regression net. |
| 7 | Lead in CRM dashboard | **A:** `GET /api/v1/leads`; **B:** `test_leads_api_integration.py` | UI list: manual or future Playwright with proxied `/api/v1/leads`. |
| 8 | Superadmin inspects platform | **A:** promote role + `GET /api/v1/admin/platform/session`; **B:** `test_rbac_authz_integration.py`, `superadmin-routing.spec.ts` | Broader admin APIs: `test_platform_admin_overview_integration.py`. |
| 9 | Suspended user / platform-suspended bot | **B:** `test_admin_moderation_integration.py` | **A** references these scenarios; do not duplicate full matrices in the MVP journey file. |
| 10 | Observability / logging sanity | **A:** `GET /api/v1/health` + security header on an authenticated JSON route | Structured logs: verify in deployment (`docs/deployment/RUNBOOK.md`); optional `tests/test_hardening_security.py` for header/error-shape regressions. |

## Environment assumptions

### pytest integration (layer A/B)

- **`TEST_DATABASE_URL`** (preferred) or host-reachable **`DATABASE_URL`** (not `@postgres:` when running on the host).
- **`JWT_SECRET_KEY`** — at least 32 characters (tests set this in-module).
- **`GEMINI_API_KEY`** — placeholder is fine when the provider is patched; required only if you remove the patch.
- **`APP_RATE_LIMITING_ENABLED=false`** — recommended for stable integration runs (set in the MVP journey module).
- Object storage: not required for PDF upload tests that **mock** `object_storage_from_settings` (same pattern as `test_bot_knowledge_files_api_integration.py`).

### Playwright (layer C)

- Next dev server on **`E2E_PORT`** (default `3002`), started by Playwright config.
- **Real backend:** either  
  - `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` (used by other real-backend specs for `request.fetch`), or  
  - `E2E_REAL_BACKEND=1` with FastAPI on **`127.0.0.1:8000`** so **browser** calls to same-origin `/api/*` rewrite correctly.
- Database must match the running API (migrations applied).

## Commands (quick reference)

```bash
# API MVP chain (PostgreSQL required)
set TEST_DATABASE_URL=postgresql://...
python -m pytest tests/test_mvp_product_journey_integration.py -m "integration and mvp_journey" -v

# Browser: landing → signup → dashboard (backend + DB required)
cd frontend
set E2E_REAL_BACKEND=1
npm run test:e2e -- e2e/mvp-landing-signup-dashboard-real.spec.ts
```

## Critical scenarios covered by `test_mvp_product_journey_integration.py`

1. Register → **`/auth/me`** → list bots (empty workspace).
2. Create bot → **GET/PATCH widget** (`welcome_text` / `theme`).
3. **POST knowledge PDF** (storage mocked; real validation + DB row).
4. **Dashboard test chat** (`/chat/test`) with deterministic fake provider.
5. **Public widget chat** (open allowlist; fake provider).
6. **CRM list** `GET /leads`.
7. **Health** + **`X-Content-Type-Options: nosniff`** on an API response.
8. **Superadmin** `GET /admin/platform/session` after DB role promotion.

Explicitly **not** reimplemented in that file: full **lead capture** through widget/Telegram (flows 5–6), full **moderation** matrix (flow 9), and **production** log/metrics verification (flow 10) — those stay in the listed focused tests and ops runbooks.
