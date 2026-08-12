# Release health & regression board

**Audience:** CTO, PM, QA, DevOps — **one page** to see integration, E2E, load, DB, and release-gate posture for a **single release candidate**.

**How to use**

1. For each candidate SHA / version, copy [templates/release-health-report.template.md](./templates/release-health-report.template.md) to `docs/release/records/YYYY-MM-DD-<version>-health.md` (or your ticket tool).
2. Fill **evidence links** (CI runs, artifacts, k6 JSON, EXPLAIN notes). No link → **unknown** (treat as risk).
3. Compare the **trend** row to the previous release record in `docs/release/records/`.
4. Final approval still goes through [RELEASE_READINESS_GATE.md](./RELEASE_READINESS_GATE.md).

---

## 1. Dashboard structure (single report)

### A. Executive rollup (30-second read)

| Pillar | Status | One-line note |
|--------|--------|----------------|
| **CI (unit + gates)** | GREEN / YELLOW / RED | e.g. main green; job X flaky |
| **Integration** | | host Postgres suite |
| **Real-stack E2E** | | Playwright workflow or equivalent |
| **Load (k6)** | | staging profile + thresholds |
| **DB regression** | | migrations + EXPLAIN / hotspot |
| **Release gate** | | G1–G12 from readiness gate |

**Rules:** **RED** if any mandatory pillar fails threshold without signed waiver. **YELLOW** = passed with waiver, flaky CI, or missing optional evidence. **GREEN** = all mandatory thresholds met with evidence linked.

### B. Detail matrix (evidence-based)

| Track | Metric | Threshold (PASS) | Actual (this release) | Evidence link | vs previous release |
|-------|--------|------------------|------------------------|---------------|---------------------|
| CI | `ci.yml` conclusion | `success` on promoting SHA | | Actions run URL | same / better / worse |
| CI | Backend pytest (non-integration) | 0 failures | | log artifact / job step | |
| CI | Frontend lint / test / build | all steps success | | | |
| CI | Alembic upgrade (CI Postgres) | success | | | |
| Integration | pytest `-m integration` | 0 failures (or agreed skip list) | | log file / CI job | |
| E2E | `e2e-real-stack.yml` or equivalent | `success` | | run URL + Playwright report | |
| Load | k6 `http_req_failed` | &lt; 2% (standard) or &lt; 5% (smoke) | | summary + optional JSON | Δ p95 key endpoints |
| Load | k6 checks pass rate | ≥ 95% (standard) or ≥ 90% (smoke) | | | |
| DB | Migrations on staging | applied, no error | | deploy / alembic log | |
| DB | Hotspot / EXPLAIN | no new full-seq-scan regression on listed queries | | link to note or `DATABASE_HOTSPOTS` run | |
| Gate | [RELEASE_READINESS_GATE](./RELEASE_READINESS_GATE.md) | GO or CONDITIONAL | | link to sign-off | |

### C. Regressions (explicit)

| ID | Symptom | First seen | Severity | Owner | Block release? |
|----|---------|------------|----------|-------|----------------|
| REG-1 | | | S1–S4 | | yes / no |

*(S1 = blocker, S2 = major, S3 = minor, S4 = cosmetic / doc)*

### D. Links block (paste once per report)

```text
Repository:     https://github.com/<org>/botforge_ai
Promoting SHA:  <full 40-char sha>
Short SHA:      <7-char>
CI (main):      https://github.com/<org>/botforge_ai/actions/workflows/ci.yml?query=branch%3Amain
E2E workflow:   https://github.com/<org>/botforge_ai/actions/workflows/e2e-real-stack.yml
This CI run:    https://github.com/<org>/botforge_ai/actions/runs/<run_id>
Playwright:     <artifact or external report URL>
k6 JSON:        <artifact URL or object storage path>
Release gate:   <ticket or docs/release/records/...>
```

---

## 2. CI artifact linking strategy

| Source | What to link | Where it lives |
|--------|----------------|----------------|
| **GitHub Actions** | Run summary page | `https://github.com/<org>/<repo>/actions/runs/<run_id>` — stable, shows conclusion + SHA |
| **Job logs** | Failing step log | Same run → job → “View raw log” or downloaded `logs_<job>.zip` from run summary |
| **Artifacts** | Playwright report, `results.json`, screenshots | Run page → **Artifacts** section (retention: set org/repo policy, typically 90 days) |
| **Reusable query** | Latest green main | `https://github.com/<org>/<repo>/actions/workflows/ci.yml?query=branch%3Amain+is%3Asuccess` (verify latest matches SHA) |
| **PR / release** | Pre-merge gate | Link the **exact** run for the merge commit, not “latest main” |

**Practice:** In the health report, require **at least** the **run URL** + **commit SHA** visible on that run. For E2E and k6, attach **artifact** or store in shared drive / S3 with a dated path: `release-artifacts/2026-04-09/v1.2.3/k6-summary.txt`.

**Automation (optional):** CI can append a row to a JSON file or post to Slack with `run_id` and `conclusion` using `github.event` — out of scope here; human-copied links are the MVP.

---

## 3. Threshold definitions

### 3.1 CI & tests

| Check | PASS | FAIL |
|-------|------|------|
| `ci.yml` on candidate SHA | All required jobs success | Any required job failure or cancelled |
| Backend unit | `pytest -m "not integration"` exit 0 | Any failure |
| Integration | All selected integration tests pass; skips documented | Undocumented failure |
| E2E real stack | Workflow success for this SHA **or** signed equivalent | Failure or not run without waiver |

### 3.2 Load (k6)

Aligned with [load/k6/README.md](../../load/k6/README.md). Profile via `THRESHOLD_PROFILE`.

| Profile | `http_req_failed` | Checks pass | `http_5xx_total` (typical run) | Health p95 |
|---------|---------------------|------------|--------------------------------|------------|
| **smoke** | &lt; 5% | ≥ 90% | &lt; 50 | &lt; 800 ms |
| **standard** (staging gate) | &lt; 2% | ≥ 95% | &lt; 10 | &lt; 400 ms |

Widget chat p95 is dominated by LLM; compare **trend vs previous release** rather than an absolute ceiling. **Regression** = p95 or failure rate **worse by &gt; 25% relative** vs last green staging run (document baseline).

### 3.3 DB regression

| Check | PASS | FAIL |
|-------|------|------|
| Migrations | Upgrade completes on staging clone | Error or manual hotfix required |
| Planner | No new sequential scan on `leads` list / admin list paths vs documented baseline | New full scan on hot path without index plan |
| Locks | No unexplained migration lock &gt; agreed SLO | Blocking incident |

Use [docs/db/DATABASE_HOTSPOTS.md](../db/DATABASE_HOTSPOTS.md) for query templates.

### 3.4 Release gate

Threshold = **GO** or **CONDITIONAL GO** per [RELEASE_READINESS_GATE.md](./RELEASE_READINESS_GATE.md); **NO-GO** blocks leadership approval regardless of other green pillars.

---

## 4. Trend comparison (across releases)

For each new report, add one row to a running **history table** (bottom of the record file or a shared spreadsheet):

| Version | SHA (short) | CI | Int | E2E | Load | DB | Gate | Notes |
|---------|-------------|----|-----|-----|------|-------|------|-------|
| v1.2.2 | abc1234 | G | G | G | G | G | GO | baseline |
| v1.2.3 | def5678 | G | G | G | Y | G | COND | k6 waiver |

**Regression rule of thumb:** Moving from **G → Y** or **G → R** on any mandatory pillar without waiver = **stop the line** for production.

**Feasible automation later:** nightly workflow exports `conclusion` + `duration` to JSON; this doc stays the **human-facing** rollup.

---

## 5. Sample status output

Below is **example** text leadership might see in Slack or Confluence (filled from a real run).

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 BotForge AI — Release health  v1.4.0-rc1  (sha: 9f3c2b1)
 Date: 2026-04-09 UTC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLLUP
  CI (unit + build)     GREEN   https://github.com/org/botforge_ai/actions/runs/12345678
  Integration           GREEN   42 passed, 0 failed (log: ticket ATT-901)
  E2E real-stack        GREEN   https://github.com/org/botforge_ai/actions/runs/12345680
  Load (k6 standard)    YELLOW  http_req_failed 1.8% (PASS); widget_chat p95 +18% vs v1.3.0 — see waiver R3
  DB                    GREEN   alembic head applied; EXPLAIN leads list = Index Scan
  Release gate          CONDITIONAL GO — waiver R3 signed by CTO

REGRESSIONS
  None blocking (REG: none)

TREND (load p95 widget_chat, staging)
  v1.3.0: 38.2s   →   v1.4.0-rc1: 45.1s  (+18%)

NEXT ACTION
  PM + QA acknowledge LLM latency drift; ship v1.4.0 to staging only until prod sign-off.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. Related files

| File | Role |
|------|------|
| [templates/release-health-report.template.md](./templates/release-health-report.template.md) | Blank report to copy per release |
| [templates/release-health.schema.json](./templates/release-health.schema.json) | Optional JSON shape for CI/dashboard export |
| [RELEASE_READINESS_GATE.md](./RELEASE_READINESS_GATE.md) | Formal G1–G12 gate + sign-off |
| [load/k6/BENCHMARK_REPORT_TEMPLATE.md](../../load/k6/BENCHMARK_REPORT_TEMPLATE.md) | Deep dive for load metrics |
| [docs/db/DATABASE_HOTSPOTS.md](../db/DATABASE_HOTSPOTS.md) | DB verification templates |
