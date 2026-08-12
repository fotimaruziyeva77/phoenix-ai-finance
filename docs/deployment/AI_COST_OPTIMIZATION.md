# AI cost optimization (sales funnel + RAG)

This note complements [PRODUCTION_ENV.md](./PRODUCTION_ENV.md).

## What changed (summary)

1. **Sales intent** — By default, ambiguous utterances **no longer call Gemini** for intent when rule-based classification misses. The orchestrator uses **`sales_default`** (`sales_interest`, confidence 0.55) so the state machine keeps a *known* intent without a second model round-trip. Restore legacy behavior with `APP_AI_SALES_USE_MODEL_FOR_INTENT_WHEN_RULES_MISS=true`.
2. **Rule shortcuts** — Short acknowledgments (`thanks`, `ok`, `yes`, …) classify as **`sales_interest`** via rules (deterministic tests in `tests/test_intent_classifier_service.py`).
3. **Intent cache** — In-process TTL cache for identical `(message prefix, niche, flags)` keys (`APP_AI_INTENT_CLASSIFIER_CACHE_*`). Set TTL to `0` to disable.
4. **RAG token budget** — Non-sales dashboard chat applies **`APP_AI_KNOWLEDGE_CHAT_CONTEXT_TOKEN_BUDGET_FRACTION`** (default `0.85`) to the default estimated-token budget when selecting knowledge chunks (lowers average prompt size).
5. **Instrumentation** — `ai_usage_logs.step_kind` distinguishes **`intent_classifier`** vs **`chat_completion`**. Structured log **`sales_turn_ai_cost_breakdown`** summarizes intent source and chat tokens per sales turn. Provider logs include optional **`ai_step_kind`**.

## Before / after measurement

**SQL (per conversation, after migration):**

```sql
SELECT conversation_id,
       step_kind,
       COUNT(*) AS calls,
       SUM(tokens_total) AS tokens,
       SUM(cost_usd) AS cost_usd
FROM ai_usage_logs
WHERE created_at > now() - interval '7 days'
GROUP BY 1, 2
ORDER BY 1, 2;
```

**Compare** median `SUM(cost_usd)` per `conversation_id` week-over-week after deploy. Expect fewer rows with `step_kind = intent_classifier` for sales traffic when the Gemini intent path is off.

**Logs:** filter `sales_turn_ai_cost_breakdown` and compare `intent_source` distribution (`sales_default` vs `gemini` vs `rules`).

## Quality / predictability

- **State machine:** `sales_default` still yields `ConversationDetectedIntent.sales_interest`, which satisfies `_intent_known` the same as a confident model label — transitions match the **`sales_interest`** path in `conversation_state_machine.py`.
- **Safeguards:** `effective_routing_intent` only downgrades low-confidence **`gemini`** labels; `sales_default` and **`rules`** pass through unchanged.
- **Regression:** Run `pytest tests/test_intent_classifier_service.py tests/test_sales_safeguards.py tests/test_conversation_state_machine.py tests/test_sales_orchestrator_integration.py`.

## Batch inference

Not implemented: the Gemini API is called per turn. Documented as a future optimization if the product needs batched intent scoring across sessions.
