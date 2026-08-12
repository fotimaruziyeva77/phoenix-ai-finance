# Release readiness gate (staging / production)

**Purpose:** Single **reusable** go/no-go framework for BotForge AI. A release is **not approved** without **measurable evidence** attached to each mandatory row (CI run, report, screenshot, log excerpt, or monitoring link).

**Companion docs:** [MVP_RELEASE_CHECKLIST.md](./MVP_RELEASE_CHECKLIST.md) (practical smoke items), [ENV_CONFIG_CHECKLIST.md](./ENV_CONFIG_CHECKLIST.md), [MIGRATION_AND_PROMOTION_ORDER.md](./MIGRATION_AND_PROMOTION_ORDER.md), [docs/deployment/RUNBOOK.md](../deployment/RUNBOOK.md).

**Release record:** For each cut, copy the **sign-off template** at the bottom into a ticket or `docs/release/records/YYYY-MM-DD-<version>.md` and attach evidence links.

---

## 1. Go / no-go checklist (PASS criteria)

Mark **PASS** only when the criterion is true **and** evidence is recorded (see §3).

| # | Area | PASS (all must hold for GO) |
|---|------|----------------------------|
| **G1** | **Auth / session security** | Strict tier: `JWT_SECRET_KEY` ≥ 32 chars; cookie auth (if enabled) uses `Secure`/`HttpOnly`/`SameSite` per [PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md); refresh rotation + CSRF policy for cookie mode documented and spot-tested; `APP_EXPOSE_ERROR_DETAILS=false` in prod; no secrets in client bundles beyond public config. |
| **G2** | **CI + integration suite** | Default branch [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) **green** for the promoting commit (Ruff, pytest `-m "not integration"`, frontend lint/test/build, embed widget, Alembic upgrade). Integration suite executed for **this candidate** on host-reachable Postgres with outcomes recorded ([docs/qa/CI_INTEGRATION.md](../qa/CI_INTEGRATION.md), [MVP_E2E_VERIFICATION.md](../qa/MVP_E2E_VERIFICATION.md)). |
| **G3** | **Real-stack E2E** | [`.github/workflows/e2e-real-stack.yml`](../../.github/workflows/e2e-real-stack.yml) **green** for this SHA **or** equivalent Playwright real-stack run documented with logs; covers dashboard/auth/bot flows per [E2E_REAL_STACK.md](../qa/E2E_REAL_STACK.md). |
| **G4** | **Widget security / origin policy** | Allowlist behavior verified: bootstrap/chat reject disallowed `Origin`/`Referer`; allowed domain matches [public-widget-origin-policy.md](../security/public-widget-origin-policy.md); rate limits and abuse hooks understood ([RATE_LIMITING_REDIS.md](../deployment/RATE_LIMITING_REDIS.md)). |
| **G5** | **Telegram setup validation** | If Telegram is in scope: webhook URL, token storage, provisioning status, and inbound→reply path verified on staging; secrets per [telegram-integration-secrets-key.md](../telegram-integration-secrets-key.md) and [PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md). If out of scope: **N/A** with written scope line. |
| **G6** | **AI caps and cost dashboards** | Caps / guardrails per [AI_USAGE_CAPS.md](../deployment/AI_USAGE_CAPS.md) and cost posture per [AI_COST_OPTIMIZATION.md](../deployment/AI_COST_OPTIMIZATION.md); owner-visible or ops-visible usage path smoke-tested; provider keys and budgets acknowledged by owner. |
| **G7** | **Queue / worker health** | If async ingestion or workers are enabled: worker process up, queue depth acceptable, failed job visibility (logs/metrics); knowledge pipeline aligns with [KNOWLEDGE_INGESTION.md](../deployment/KNOWLEDGE_INGESTION.md). If single-process only: **N/A** with architecture note. |
| **G8** | **Load test thresholds** | k6 (or equivalent) run against **staging** (not prod) with results vs thresholds; see [load/k6/README.md](../../load/k6/README.md) and [load/k6/BENCHMARK_REPORT_TEMPLATE.md](../../load/k6/BENCHMARK_REPORT_TEMPLATE.md). **PASS** = thresholds met **or** documented waiver with risk accepted in §2. |
| **G9** | **DB hotspot review** | Migrations for this release applied on staging; [DATABASE_HOTSPOTS.md](../db/DATABASE_HOTSPOTS.md) reviewed; for risky schema changes, `EXPLAIN (ANALYZE, BUFFERS)` samples before/after attached or linked. |
| **G10** | **Rollback validation** | Prior **image tag / artifact** recorded; rollback path rehearsed or documented: app = redeploy previous artifact; DB = forward-fix or restore per [RUNBOOK.md](../deployment/RUNBOOK.md) — **no** undocumented downgrade scripts in prod. |
| **G11** | **Superadmin support tooling** | Superadmin-only APIs (overview, moderation if used) verified: authorized user succeeds, non-superadmin **403**; tenant inspection flows match [RELEASE_PROCESS.md](../deployment/RELEASE_PROCESS.md) / ops practice. |
| **G12** | **Known limitations** | [ARCHITECTURE_MVP.md](./ARCHITECTURE_MVP.md) (or release-specific addendum) updated: product/ops limitations, non-goals, and customer-facing caveats for this version. |

**GO:** G1–G4 mandatory always; G5–G7 **PASS** or **N/A (documented)**; G8–G12 **PASS** or **explicit waiver** in risk register with approver.

**NO-GO:** Any mandatory **FAIL** without signed waiver; CI red; undeclared breaking schema change; auth/session regression on staging.

---

## 2. Risk register (release-specific)

Copy this table into the release ticket and fill **before** sign-off.

| ID | Risk | Likelihood (L) / Impact (I) | Mitigation | Evidence / trigger | Owner | Status (open / mitigated / accepted) |
|----|------|------------------------------|------------|-------------------|-------|--------------------------------------|
| R1 | | L: / I: | | | | |
| R2 | | | | | | |

**Examples to consider:** Redis unavailable → rate limits fail-open/fail-closed behavior; LLM provider outage; Telegram webhook DNS; migration lock duration; load test not run → performance unknown.

---

## 3. Required evidence table

Each **mandatory** row needs a **link or attachment** (no “trust me”).

| Gate ID | Evidence type | Example | Stored where |
|---------|---------------|---------|--------------|
| G1 | Config audit + spot test notes | Redacted env checklist, cookie screenshot, auth flow notes | Ticket / release record |
| G2 | CI run URL + integration summary | GitHub Actions run id, pytest integration log | Ticket |
| G3 | E2E run URL or report | `e2e-real-stack` workflow run, Playwright report artifact | Ticket / CI artifacts |
| G4 | Test log or script output | Widget negative-origin curl/httpie transcript | Ticket |
| G5 | Staging Telegram trace | Webhook delivery log, test message id | Ticket |
| G6 | Screenshot or API response | Usage/caps dashboard or admin aggregate snippet | Ticket |
| G7 | Metric or log excerpt | Worker heartbeat, queue depth graph | Observability ([OBSERVABILITY.md](../deployment/OBSERVABILITY.md)) |
| G8 | k6 summary + optional JSON | Pasted summary + `results.json` | Ticket or `load/k6/` archive path |
| G9 | Migration log + EXPLAIN | Alembic output, `EXPLAIN` paste | Ticket |
| G10 | Rollback doc + tag | Previous image digest, RUNBOOK section reference | Ticket |
| G11 | API test transcript | 200 vs 403 samples with redacted JWT meta | Ticket |
| G12 | Doc link | Commit hash of `ARCHITECTURE_MVP.md` or addendum PR | Ticket |

---

## 4. Sign-off template (CTO / PM / QA / DevOps)

**Release:** `v________` **Git SHA:** `________` **Target:** `staging` / `production` **Date (UTC):** `________`

| Role | Name | Decision (GO / NO-GO / CONDITIONAL) | Conditions (if any) | Signature / date |
|------|------|-------------------------------------|---------------------|------------------|
| **Engineering / CTO** | | | | |
| **Product (PM)** | | | | |
| **QA** | | | | |
| **DevOps / SRE** | | | | |

**Conditional GO** is allowed only if:

1. Conditions are **finite** (e.g. “enable feature flag X after 24h soak”), and  
2. **Owner** and **due date** are listed below.

**Conditions list:**

- [ ] …

**Record retention:** Keep this sign-off and evidence links for **≥** the same period as your compliance / incident policy.

---

## 5. Quick reference map

| Topic | Doc |
|--------|-----|
| Env vars | [ENV_CONFIG_CHECKLIST.md](./ENV_CONFIG_CHECKLIST.md), [PRODUCTION_ENV.md](../deployment/PRODUCTION_ENV.md) |
| Observability & Sentry | [OBSERVABILITY.md](../deployment/OBSERVABILITY.md), [RUNBOOK.md](../deployment/RUNBOOK.md) |
| CI details | [CI_INTEGRATION.md](../qa/CI_INTEGRATION.md) |
| Staging deploy | [CI_CD_STAGING.md](../deployment/CI_CD_STAGING.md), [deploy-staging workflow](../../.github/workflows/deploy-staging.yml) |
| Load testing | [load/k6/README.md](../../load/k6/README.md) |
| DB performance | [DATABASE_HOTSPOTS.md](../db/DATABASE_HOTSPOTS.md) |
