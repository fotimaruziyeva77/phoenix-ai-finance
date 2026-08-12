# BotForge AI — load test benchmark report

**Run ID:**  
**Date (UTC):**  
**Environment:** (e.g. staging EU, compose on CI runner)  
**k6 version:**  
**Git SHA / release:**  

## Scope

| Flow | Scenario name | Notes |
|------|---------------|--------|
| Public widget | `widget_bootstrap`, `widget_chat` | AI latency dominates chat |
| Auth | `auth_login` | Per-VU login; watch 401 vs 429 |
| CRM / leads | `leads_list` | GET `/api/v1/leads` (creation is pipeline-driven from conversations) |
| Ingestion | `knowledge_upload` | Optional; queue/worker saturation |

## Environment assumptions

- **BASE_URL** reachable from runner; TLS as in production if applicable.
- **Redis** for rate limits: same mode as target (in-process vs Redis); limits are **per client IP** for public widget (all k6 VUs often share one IP → rate limits appear early).
- **PUBLIC_WIDGET_KEY** and **WIDGET_ORIGIN** valid for allowlisted bootstrap/chat.
- **LOADTEST_*** credentials: dedicated account; bearer JSON tokens (cookie-only auth needs k6 cookie jar — not covered by default script).

## Configuration

| Parameter | Value |
|-----------|--------|
| Threshold profile | |
| Max VUs (peak) | |
| Duration | |
| Think time | |

## Results summary

Paste k6 end-of-test summary or `k6 run --out json=results.json` highlights.

| Metric | Value | Threshold | Pass |
|--------|--------|-----------|------|
| http_req_failed (rate) | | | |
| p95 http_req_duration (health) | | | |
| p95 http_req_duration (bootstrap) | | | |
| p95 http_req_duration (login) | | | |
| p95 http_req_duration (leads_list) | | | |
| p95 http_req_duration (widget_chat) | | | |
| Checks success rate | | | |
| HTTP 429 count / rate | | (expected under probe) | |

## Rate limiting

- Observed **429** on which endpoints?
- Alignment with configured limits (widget chat/min, bootstrap/min, login/min)?

## Saturation & bottlenecks

- **First limiting factor:** (CPU, DB pool, Redis, LLM provider, worker queue depth, egress, etc.)
- **Symptoms:** (rising latency, 5xx, timeouts, queue lag)
- **Approximate knee in load:** (VUs or RPS before SLO breaks)

## Recommendations

1.  
2.  
3.  

## Sign-off

**Engineer:**  
**Ready for release:** yes / no / with conditions  
