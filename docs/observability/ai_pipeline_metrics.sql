-- AI pipeline metrics from ai_usage_logs (Postgres).
-- step_kind values: trivial_handled, exact_cache_hit, semantic_cache_hit, llm_call, synthetic_output, intent_classifier
-- Join with structured logs (event=ai_pipeline_turn) in your log store for tokens_saved_est.

-- Average total tokens per request (UTC day)
SELECT
    date_trunc('day', created_at AT TIME ZONE 'UTC') AS usage_day_utc,
    AVG(tokens_total)::numeric(12, 2) AS avg_tokens_per_request,
    COUNT(*) AS requests
FROM ai_usage_logs
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1 DESC;

-- Share of pipeline outcomes (last 7 days)
SELECT
    step_kind,
    COUNT(*) AS n,
    round(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM ai_usage_logs
WHERE created_at >= now() - interval '7 days'
  AND step_kind IS NOT NULL
GROUP BY step_kind
ORDER BY n DESC;

-- % trivial / exact / semantic / llm (chat path only)
SELECT
    round(100.0 * SUM(CASE WHEN step_kind = 'trivial_handled' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS pct_trivial,
    round(100.0 * SUM(CASE WHEN step_kind = 'exact_cache_hit' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS pct_exact_cache,
    round(100.0 * SUM(CASE WHEN step_kind = 'semantic_cache_hit' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS pct_semantic_cache,
    round(100.0 * SUM(CASE WHEN step_kind = 'llm_call' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS pct_llm_call
FROM ai_usage_logs
WHERE created_at >= now() - interval '7 days';

-- Total estimated cost per calendar day (UTC)
SELECT
    (created_at AT TIME ZONE 'UTC')::date AS usage_date_utc,
    COALESCE(SUM(cost_usd), 0)::numeric(16, 8) AS total_cost_usd,
    SUM(tokens_total) AS total_tokens
FROM ai_usage_logs
WHERE created_at >= now() - interval '30 days'
GROUP BY 1
ORDER BY 1 DESC;

-- Per-bot daily rollup (same grain as daily_ai_usage_aggregates when populated)
SELECT
    bot_id,
    (created_at AT TIME ZONE 'UTC')::date AS d,
    COUNT(*) AS requests,
    SUM(tokens_total) AS tokens,
    COALESCE(SUM(cost_usd), 0)::numeric(16, 8) AS cost_usd
FROM ai_usage_logs
WHERE created_at >= now() - interval '14 days'
GROUP BY bot_id, d
ORDER BY d DESC, tokens DESC;
