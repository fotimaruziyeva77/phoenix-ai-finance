# Architecture summary and MVP verdict — BotForge AI

## Executive verdict

**Verdict: MVP-ready modular monolith** — one deployable **FastAPI** backend (`app/`) with clear service and repository boundaries, **PostgreSQL** as system of record, **Next.js** dashboard, **embeddable widget** and **Telegram** as first-class conversation channels. The design supports **four primary niches** plus a **generic** fallback flow, a **lead pipeline** tied to sales conversations, **PDF knowledge** with retrieval, and **superadmin** platform controls.

This is **not** a microservices platform: scale-out, queue-backed workers, and multi-region are **future work**. What ships for MVP is intentional cohesion and operable defaults.

---

## 1. Modular monolith

| Layer | Role |
|-------|------|
| `app/api/` | HTTP routers, deps, rate limits |
| `app/services/` | Use cases (bots, AI, leads, widget, Telegram, moderation) |
| `app/repositories/` | Persistence access |
| `app/models/` | SQLAlchemy ORM |
| `app/lib/` | Domain rules (niches, widget origin, scoring, etc.) |

**Strengths:** Testable services, shared transaction boundaries, single migration stream (Alembic).

**MVP limitation:** Long-running jobs (heavy PDF processing at scale) share the API process unless you add workers later.

---

## 2. Four niche-ready design (+ generic)

- **Registry:** `app/lib/niche_registry.py` — `education`, `healthcare`, `dev_agency`, `services` with default lead fields and copy.
- **Conversation flows:** `app/lib/niche_flow/` — per-niche `NicheConversationFlowDefinition` (qualification goals, core fields, funnel shape).
- **Generic:** `niche_id=generic` uses `GENERIC_CONVERSATION_FLOW` in `app/lib/niche_flow/registry.py` for bots outside the four presets.

**MVP-grade:** Adding a fifth niche requires code changes (registry + flow module + frontend constants), not runtime admin UI.

---

## 3. Multi-channel: widget + Telegram

- **Web widget:** Public key, origin allowlist (or open mode when allowlist empty), shared **AIService** / orchestrator path; conversations tagged with web widget channel.
- **Telegram:** Adapter + webhook path; same orchestrator and **lead creation** semantics where sales goals apply; `source_channel` on leads/conversations for analytics.

**MVP limitation:** True end-to-end browser widget + Telegram tests need live origins and BotFather tokens; integration tests cover logic with DB + HTTP where possible ([docs/qa/MVP_E2E_VERIFICATION.md](../qa/MVP_E2E_VERIFICATION.md)).

---

## 4. Lead pipeline

- **Creation:** `LeadCreationService` — sales bots, funnel state (e.g. closing/completed), niche-required fields including **phone**, dedupe/idempotency rules (`lead_creation_service` docstring summarizes reasons).
- **CRM API:** Owner-scoped list/detail/status (`app/api/v1/leads.py`); `LeadPipelineService` + policies for valid transitions.
- **Model:** `Lead` status enum and JSON payloads; **no** separate lead activity/history table in MVP (see `app/models/lead.py` docstring).

**MVP-grade:** Pipeline is usable for single-owner workspaces; advanced CRM (teams, SLA, full audit timeline) is future work.

---

## 5. Knowledge engine

- **Upload:** PDF to object storage (S3-compatible), metadata in DB.
- **Processing:** Extraction pipeline into chunks; **FTS** retrieval scoped per bot (`KnowledgeRetrievalService` path).
- **Chat:** RAG-style prompt extension in `AIService` when knowledge exists.

**MVP limitation:** Large files and burst upload load are bounded by API/process capacity; no separate search cluster.

---

## 6. Superadmin control

- **RBAC:** `UserRole.superadmin` vs `customer_admin`; JWT carries role.
- **APIs:** Platform session, user/bot lists and detail, **moderation** (suspend user/bot, activate) with audit metadata (`test_admin_moderation_integration.py` reflects behavior).
- **Frontend:** `/superadmin` shell gated by role.

**MVP limitation:** No delegated org-admin hierarchy; superadmin is global platform operator.

---

## 7. CI and observability foundations

- **CI** (`.github/workflows/ci.yml`): lint, unit tests, frontend/widget build, migration apply to ephemeral Postgres.
- **Health:** `GET /api/v1/health` — synthetic liveness ([`health_service`](../../app/services/health_service.py)).
- **Logging:** Structured logging; optional JSON; request logging toggles via `Settings`.
- **Sentry:** Optional via DSN env vars ([PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md)).

**MVP limitation:** No built-in metrics server or distributed tracing in-repo; add via platform (Datadog, Prometheus sidecar, etc.). **In-memory rate limits** do not coordinate across workers — document when scaling horizontally.

---

## Non-blocking known limitations (explicit)

These are **accepted for MVP** if product and ops sign off; track as follow-ups.

1. **Horizontal scaling:** Per-IP / per-widget limits and some abuse state are process-local.
2. **Lead E2E automation:** Full multi-turn sales dialog to a lead row is validated primarily by integration tests + staging manual QA, not a single flaky browser test.
3. **Python/toolchain:** The repo **standardizes on Python 3.12** (Docker image, GitHub Actions, `pyproject.toml` / `.python-version`). Use 3.12 locally to match CI and production containers; other versions are unsupported for release gates.
4. **Next.js / OneDrive:** Dev on synced folders can hit `readlink` issues under `.next`; prefer non-synced clone for reliable local E2E.
5. **Gunicorn multi-worker:** Not wired in repo; RUNBOOK documents Uvicorn; production process model is operator-defined.
6. **Deploy automation:** Staging workflow validates Docker build; registry push and cluster apply are **out of repo** until you add them.
7. **Lead pipeline audit trail:** Status changes are not persisted as an append-only event stream in MVP.

---

## Non-blocking follow-up backlog (suggested)

| Item | Rationale |
|------|-----------|
| Redis-backed rate limits / abuse | Multi-worker and DDoS resilience |
| Background queue for PDF processing | Isolate CPU/IO from API latency |
| GitHub Actions: integration pytest job with Postgres service | Catch DB regressions every PR |
| Real-backend Playwright in CI | Optional; needs API + DB job wiring |
| Metrics + SLO dashboards | Production operability |
| Lead activity / status history table | CRM depth, compliance |

---

## Final architecture statement

The codebase delivers a **coherent MVP**: one API, one DB, explicit niche and channel modeling, real lead and knowledge paths, and superadmin safety valves. **Ship when** checklist + staging smoke pass **and** limitations above are acknowledged—not when every future-scale concern is solved.
