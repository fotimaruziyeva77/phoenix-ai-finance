# Observability: releases, correlation, and alerts

This document complements [PRODUCTION_ENV.md](./PRODUCTION_ENV.md) and the [RUNBOOK](./RUNBOOK.md).

## Releases (Sentry)

| Surface | How release is set |
|---------|-------------------|
| **API container** | Build args / env: `APP_VERSION`, `SENTRY_RELEASE` (see `Dockerfile`, `docker-compose.yml`, GitHub `deploy-staging.yml` / `release-image.yml`). `app/core/error_tracking.py` uses `SENTRY_RELEASE` / `APP_SENTRY_RELEASE`, then `APP_VERSION`. |
| **Knowledge worker** | Same image/env as API; `init_error_tracking` runs on startup. |
| **Next.js dashboard** | `NEXT_PUBLIC_SENTRY_RELEASE` at **build** time; optional `SENTRY_RELEASE` for server-side init. Source maps: set `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` during `next build`. |

## Request correlation

- **API:** `X-Request-ID` and `X-Correlation-ID` (see `app/core/middleware.py`, `app/core/request_log_context.py`). Responses echo the same headers. JSON errors include `request_id` where applicable.
- **Optional:** Ingress can send W3C `traceparent`; the API binds `w3c_trace_id` into structured logs and Sentry `http_safe` context (no PII).
- **Dashboard:** `frontend/src/lib/api/client.ts` sends `X-Request-ID` (per request) and `X-Correlation-ID` (per tab via `sessionStorage`). `ApiError` carries `requestId` / `correlationId` for UI and support.

## Log fields for alerting (JSON logs, `APP_LOG_JSON=true`)

Use your log platform’s query language; examples below are conceptual.

| Signal | Log markers | Suggested alert |
|--------|-------------|-----------------|
| **API 5xx spike** | `event=http_request`, `http_event=completed`, `http_status>=500` **or** `observability_signal=api_server_error` | Count per 5m vs baseline; page on sustained elevation. |
| **AI provider failures** | Sentry: domain `ai_provider`; logs: provider-specific errors | Sentry issue alerts + rate of `ai_provider` messages. |
| **AI spend spike** | DB: `ai_usage_logs.cost_usd` / `tokens_total` by hour | Scheduled SQL or BI dashboard; threshold per tenant or global. Example: `SELECT date_trunc('hour', created_at) h, sum(cost_usd) FROM ai_usage_logs WHERE created_at > now() - interval '24 hours' GROUP BY 1;` |
| **Queue / PDF ingestion** | `knowledge_ingestion_metric` with `event=dead_letter` **or** `observability_signal=queue_dead_letter` | Any dead-letter in 15m, or count > N/day. |
| **Telegram** | `telegram_channel_event` with `observability_signal=telegram_failure` or `telegram_delivery_failure` | Spike in failures or delivery failures after successful AI. |

## Sentry alert ideas

- **New issue** in environment `production` with tag `domain` in `ai_provider`, `telegram`, etc.
- **Issue frequency** regression after deploy (compare to previous `release`).
- **Performance** (if `APP_ERROR_TRACKING_TRACES_SAMPLE_RATE` or frontend `NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE` > 0): latency percentiles for key transactions.

## Security hygiene (unchanged principles)

- API Sentry `before_send` strips cookies, headers, query strings from events (`app/core/error_tracking.py`).
- Do not enable `sendDefaultPii`. Do not turn on `APP_LOG_REQUEST_BODY` in strict tiers.
- Frontend Sentry init uses `sendDefaultPii: false` and strips query strings from `request.url` in `beforeSend`.
