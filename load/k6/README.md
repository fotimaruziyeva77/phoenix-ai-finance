# BotForge AI — k6 load tests

Scripts exercise **public widget** (bootstrap + chat), **auth login**, **CRM list leads** (`GET /api/v1/leads`), an optional **rate-limit hammer** on bootstrap, and optionally **knowledge PDF upload** (queue-backed ingestion).

## Prerequisites

- [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) v0.47+ (uses `http.expectedStatuses` + scenario CLI flags).
- A running API (`BASE_URL`). For local compose, use the backend port from your `.env` / `docker-compose.yml`.
- **Never** point default credentials at production tenants; use a disposable staging workspace.

## Environment assumptions

| Variable | Required for | Notes |
|----------|----------------|-------|
| `BASE_URL` | All | e.g. `http://localhost:8000` (no trailing slash). |
| `PUBLIC_WIDGET_KEY` | Widget scenarios | From dashboard / `widget_config` for the tenant under test. |
| `WIDGET_ORIGIN` | Widget scenarios | Must match embed **domain allowlist** (sent as `Origin` / `Referer`). |
| `LOADTEST_LOGIN_EMAIL` / `LOADTEST_LOGIN_PASSWORD` | `auth_login`, `leads_list`, `knowledge_upload` | Dedicated user; **bearer tokens in JSON** assumed (cookie-only auth needs extra k6 cookie handling). |
| `LOADTEST_BOT_ID` + `LOADTEST_PDF_PATH` | `knowledge_upload` | Valid bot UUID and path to a small PDF on the runner. |
| `THRESHOLD_PROFILE` | Thresholds | `smoke` (default, loose), `standard`, `stress`. |

**Rate limits (defaults from app config):** login ~10/min/IP, public widget chat ~30/min/IP/key, bootstrap ~120/min/IP/key, knowledge upload ~20/min/owner+bot. k6 VUs often share **one egress IP**, so you will hit **429** before CPU saturates — that is a valid outcome to record (`http_429_total`), not necessarily a failure.

**Lead creation:** HTTP API exposes list/detail/patch for CRM leads; **creation is pipeline-driven** (e.g. from conversations). Load baseline for “leads path” here is **authenticated list** (`GET /api/v1/leads`). Widget **chat** covers the visitor funnel that feeds leads.

## Run

```bash
cd load/k6
k6 run botforge-load-test.js
```

Partial runs:

```bash
# CI / quick regression: no AI chat, no rate-limit storm
k6 run --exclude-scenario widget_chat --exclude-scenario rate_limit_probe botforge-load-test.js

# Widget-only
k6 run --include-scenario health_check --include-scenario widget_bootstrap --include-scenario widget_chat botforge-load-test.js

# Stricter SLOs
k6 run -e THRESHOLD_PROFILE=standard botforge-load-test.js
```

Windows PowerShell example:

```powershell
cd load\k6
$env:BASE_URL="http://localhost:8000"
$env:PUBLIC_WIDGET_KEY="your-key"
$env:WIDGET_ORIGIN="http://localhost:3000"
$env:LOADTEST_LOGIN_EMAIL="loadtest@example.com"
$env:LOADTEST_LOGIN_PASSWORD="********"
k6 run botforge-load-test.js
```

Artifacts:

```bash
k6 run --out json=results.json botforge-load-test.js
```

## What is measured

- **Latency:** `http_req_duration` tagged by `endpoint` (`health`, `widget_bootstrap`, `widget_chat`, `auth_login`, `leads_list`, `knowledge_upload`, …).
- **Errors:** `http_req_failed` (4xx/5xx and protocol errors per k6 rules); **429** is treated as *expected* for metrics tagging but counted in `http_429_total`.
- **5xx:** `http_5xx_total` counter.
- **Checks:** `checks_passed` rate (handler checks such as JSON shape).
- **Saturation:** Watch rising p95/p99, `http_5xx_total`, DB pool timeouts, worker queue depth, and LLM provider latency; compare with **when 429s appear** (limiter vs upstream).

## Recommended pass / fail (release gates)

Tune per environment; start here:

| Gate | smoke (default script profile) | standard (staging) |
|------|----------------------------------|-------------------|
| `checks` pass rate | ≥ 90% | ≥ 95% |
| `http_req_failed` | &lt; 5% | &lt; 2% |
| `http_5xx_total` | &lt; 50 over run | &lt; 10 over run |
| `health` p95 | &lt; 800 ms | &lt; 400 ms |
| `widget_bootstrap` p95 | &lt; 3 s | &lt; 1.5 s |
| `auth_login` p95 | &lt; 4 s | &lt; 2 s |
| `leads_list` p95 | &lt; 3 s | &lt; 1.5 s |
| `widget_chat` p95 | &lt; 90 s | &lt; 60 s |

**Fail** the run if **any configured threshold** fails (k6 exit code 99).

**429:** Do not treat as failure if you are validating limiter behavior. For **functional** SLO tests, lower concurrency or add think time so most requests stay **2xx**.

## Benchmark report

After each run, copy k6’s end summary and metrics into `BENCHMARK_REPORT_TEMPLATE.md` and archive with the release candidate.

## Files

| File | Purpose |
|------|---------|
| `botforge-load-test.js` | Main scenarios + thresholds |
| `env.example` | Variable reference |
| `BENCHMARK_REPORT_TEMPLATE.md` | Report structure |
| `README.md` | This document |
