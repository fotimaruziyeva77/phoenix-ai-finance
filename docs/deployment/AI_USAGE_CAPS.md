# AI usage caps (FinOps guardrails)

## Enforcement point

**Before any user message is persisted** for a turn, :meth:`~app.services.ai_service.AIService.send_bot_message` calls :meth:`~app.services.ai_usage_quota_service.AIUsageQuotaService.assert_can_consume`. That reads **already logged** ``ai_usage_logs.tokens_total`` (UTC windows). If a cap is exceeded, :class:`~app.services.ai_exceptions.AIServiceQuotaExceededError` is raised and the request is blocked **without** inserting the user chat row.

After a successful provider call, each turn still appends a usage log row; caps use **total tokens** per row (provider-reported when present, otherwise estimated for successful completions).

## Windows

- **Bot daily:** UTC calendar day; resets at next UTC midnight.
- **Owner monthly:** UTC calendar month across **all** bots owned by the user; resets on the first instant of the next month (UTC).

## Strict environments

For ``APP_ENVIRONMENT`` in ``staging`` / ``production`` / ``prod``, settings validation requires:

- ``APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT`` > 0  
- ``APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER`` > 0  

Local/docker may leave these at ``0`` to disable enforcement.

## Operator visibility

- **GET** ``/api/v1/bots/{bot_id}/ai-usage-quota`` — authenticated owner; returns current usage, caps, enforcement flags, and ``resets_at_utc`` per window.
- Structured logs: ``ai_usage_near_cap`` (INFO), ``ai_usage_quota_blocked`` (WARNING, ``metric_event=ai_usage_quota_exceeded``), ``ai_usage_quota_repo_missing`` (ERROR in strict env when caps are on but the aggregate repository is not wired).
