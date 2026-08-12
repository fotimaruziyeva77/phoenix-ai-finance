# Codebase Concerns

**Analysis Date:** 2026-05-30

---

## Tech Debt

**Single-provider AI architecture (Gemini only):**
- Issue: All AI paths are hard-coded to Gemini via `app/integrations/providers/gemini.py`. A provider abstraction (`app/ai_providers/base.py`, `app/ai_providers/registry.py`) exists, but only one concrete implementation is registered. Adding a second provider (e.g., OpenAI) requires non-trivial work.
- Files: `app/ai_providers/registry.py`, `app/integrations/providers/gemini.py`
- Impact: No fallback when Gemini is unavailable; no cost-optimization via multi-provider routing.
- Fix approach: Implement a second `AIProvider` subclass and wire it into the registry.

**Knowledge retrieval is FTS-only (no vector embeddings in Postgres):**
- Issue: `app/repositories/knowledge_retrieval_repository.py` uses PostgreSQL full-text search (`websearch_to_tsquery` / `plainto_tsquery`). Embedding vectors are computed for the semantic completion cache in Redis but are never stored in Postgres. There is no `pgvector` column or HNSW index on `knowledge_chunks`. RAG accuracy degrades for semantic / paraphrase queries.
- Files: `app/repositories/knowledge_retrieval_repository.py`, `app/models/knowledge_chunk.py`, `app/services/knowledge_retrieval_service.py`
- Impact: Low recall on synonym or concept queries; FTS `simple` config does not stem or handle cross-language.
- Fix approach: Add a `embedding vector(768)` column to `knowledge_chunks`, create a `pgvector` HNSW index, and add a hybrid FTS+vector retrieval path.

**Semantic cache scans all entries in a Redis list (O(N) per lookup):**
- Issue: `SemanticCompletionCache.lookup()` in `app/services/semantic_completion_cache.py` does an `LRANGE` on the full per-bot list (up to `ai_semantic_cache_max_entries_per_bot`, default 200) and iterates every entry in Python to compute cosine similarity.
- Files: `app/services/semantic_completion_cache.py`
- Impact: At 200 entries, each cache check deserializes ~200 JSON objects and runs 200 float-dot-products in-process. Under concurrent traffic, this blocks the event loop during vector comparison.
- Fix approach: Use Redis HNSW via `redis-py`'s `FT.SEARCH` (RediSearch module) for ANN lookup, or store embeddings in Postgres using pgvector to avoid the per-lookup O(N) Python loop.

**`SalesConversationOrchestrator` exceeds 1,500 lines:**
- Issue: `app/services/sales_conversation_orchestrator.py` is 1,543 lines — the largest file in the project. It handles intent classification, niche flow resolution, question planning, state machine transitions, LLM calls, lead capture, cache writes, and owner delivery, all in one class.
- Files: `app/services/sales_conversation_orchestrator.py`
- Impact: High cognitive load; any change risks unintended cross-cutting effects; test failures are hard to isolate.
- Fix approach: Extract lead-capture orchestration, owner-delivery routing, and cache persistence into separate service objects already partially available (`app/services/sales_lead_capture_turn.py`, `app/services/lead_owner_delivery_router.py`).

**`app/api/deps.py` is a 958-line dependency-injection monolith:**
- Issue: All FastAPI `Depends` factories live in one file. Adding any new service requires editing this file, increasing merge conflicts.
- Files: `app/api/deps.py`
- Impact: Every developer touches the same file for any new feature wiring.
- Fix approach: Split into topic modules, e.g., `deps/auth.py`, `deps/billing.py`, `deps/knowledge.py`.

**`stripe` package is an optional import with `type: ignore`:**
- Issue: `app/services/billing_service.py` lazy-imports `stripe` at call time with `# type: ignore[import-untyped]` and `# type: ignore[return]`. This means type-checking never validates Stripe API calls. Stripe SDK errors surface at runtime rather than at type-check time.
- Files: `app/services/billing_service.py` lines 140–148
- Impact: Any Stripe API signature change or misconfiguration is undetectable until production.
- Fix approach: Add `stripe` to type-checked dependencies with a stub package, or declare the method return type explicitly. At minimum, add a startup check verifying Stripe is importable when `stripe_secret_key` is set.

**Plan limits not enforced for `conversations_per_month` consistently:**
- Issue: `enforce_conversation_limit` in `app/services/billing_service.py` exists and is called from `app/api/v1/bot_chat.py`, `app/services/public_widget_chat_service.py`, and `app/services/telegram_webhook_inbound_service.py`. However, the monthly counter (`current_month_count`) is passed by callers — its computation is scattered, not centralized.
- Files: `app/services/billing_service.py`, `app/api/v1/bot_chat.py`, `app/services/telegram_webhook_inbound_service.py`
- Impact: A new entry point (e.g., a REST API webhook bot) could be added and miss the count call.
- Fix approach: Move the count query inside `enforce_conversation_limit` so callers cannot forget to pass it.

**Stripe webhook deduplication requires Redis; silently skips deduplication when Redis is absent:**
- Issue: `app/services/billing_service.py` lines 284–289 skip idempotency check if `self._redis is None`. Without Redis, replayed `checkout.session.completed` events activate a subscription multiple times.
- Files: `app/services/billing_service.py`
- Impact: Double-activations or wrong plan upgrades on Stripe replay.
- Fix approach: Persist the Stripe `event_id` to the `webhook_logs` table (already stored) and use a database-level unique check as the fallback idempotency guard.

---

## Known Bugs

**`admin_campaigns._send_campaign_emails` type annotation bypass:**
- Symptoms: Line 317 of `app/api/v1/admin_campaigns.py` uses `# type: ignore[attr-defined]` on `async_session_factory()` because the type checker cannot see through `get_session_maker()` at call time.
- Files: `app/api/v1/admin_campaigns.py` line 317
- Trigger: Always (static analysis issue); runtime works fine.
- Workaround: `noqa` suppression in place.

**`auth_cookies.py` `samesite` type coercion ignores type checker:**
- Symptoms: `app/core/auth_cookies.py` lines 43 and 77 suppress `type: ignore[arg-type]` when passing `settings.auth_cookie_same_site.lower()` to Starlette's `set_cookie`. The `SameSite` literal type is not assignable from `str`.
- Files: `app/core/auth_cookies.py`
- Trigger: Type-checker only; runtime functions correctly.
- Workaround: `type: ignore` in place.

---

## Security Considerations

**`unsafe-inline` in Content-Security-Policy `script-src`:**
- Risk: `app/core/security_headers.py` includes `'unsafe-inline'` in the `script-src` directive. This allows inline `<script>` execution and partially negates CSP XSS protection.
- Files: `app/core/security_headers.py` line 47
- Current mitigation: API-only server (no HTML rendered), but the header is still served on all responses.
- Recommendations: Remove `'unsafe-inline'` from `script-src`; use nonces or SRI hashes if inline scripts are genuinely needed. The header should reflect the API's actual surface, not a presumed frontend.

**HSTS disabled by default (`security_enable_hsts: bool = False`):**
- Risk: HTTP Strict-Transport-Security is off unless `APP_SECURITY_ENABLE_HSTS=true`. In production deployments where HTTPS is mandatory, the header may be silently absent if the operator forgets to set it.
- Files: `app/core/config.py` line 953, `app/core/security_headers.py` lines 40–44
- Current mitigation: Docs mention it is for HTTPS deployments only.
- Recommendations: Add HSTS to the `validate_production_constraints` validator (require `security_enable_hsts=true` in `production`/`staging`).

**In-memory rate limiter is not safe for multi-worker deployments:**
- Risk: `app/core/limiters/memory_sliding_window.py` is used when `RATE_LIMIT_REDIS_URL` is unset. Under multiple uvicorn workers or multiple replicas, each process maintains its own counter — effective rate limit becomes `limit × worker_count`.
- Files: `app/core/limiters/memory_sliding_window.py`, `app/core/limiters/factory.py`
- Current mitigation: Setting description explicitly warns "not safe across multiple workers."
- Recommendations: Require Redis in production/staging via the startup validator. The `validate_production_constraints` model validator in `app/core/config.py` should check `rate_limit_redis_url` when `environment` is `production` or `staging`.

**`telegram_token_fernet_key` required only in strict environments:**
- Risk: In `local`/`docker` environments, Telegram tokens stored in `telegram_configs.encrypted_bot_token` remain unencrypted (503 returned at connect time, but existing rows are cleartext until a key is set). Migrating from unencrypted to encrypted requires `scripts/reencrypt_telegram_secrets.py`.
- Files: `app/core/config.py` lines 1372–1378, `app/lib/integration_secrets_crypto.py`
- Current mitigation: Warning logged at startup; `reencrypt_telegram_secrets.py` migration script exists.
- Recommendations: Document the migration path prominently; ensure CI cannot skip it.

**Broad `except Exception` swallows errors in webhook logging paths:**
- Risk: Multiple `except Exception: pass` blocks in `app/api/v1/public_telegram.py` (lines 98–99, 120–121) and `app/api/v1/billing.py` (line 269) mean webhook log writes are fully silent on failure. A broken webhook log table would never surface an alert.
- Files: `app/api/v1/public_telegram.py`, `app/api/v1/billing.py`, `app/services/lead_owner_delivery_router.py`
- Current mitigation: `noqa: BLE001` is documented as intentional.
- Recommendations: Log the suppressed exception at WARNING level rather than silently passing.

---

## Performance Bottlenecks

**`User` model eagerly loads all relationships (`lazy="selectin"`):**
- Problem: `app/models/user.py` declares 9 relationships (`oauth_accounts`, `bots`, `conversations`, `leads`, `knowledge_files`, `knowledge_chunks`, `widget_configs`, `telegram_configs`, `subscription`) all with `lazy="selectin"`. Any query that fetches a `User` row issues up to 9 additional SELECTs automatically.
- Files: `app/models/user.py` lines 106–161
- Cause: `lazy="selectin"` was chosen as a safe default to avoid sync lazy-load errors, but it is applied globally rather than per-call-site.
- Improvement path: Switch model relationships to `lazy="raise"` (no implicit loading) and use explicit `selectinload()` options only on queries that need the related data.

**`Bot` model also eager-loads all 9 relationships:**
- Problem: Same pattern as `User`: `app/models/bot.py` has 9 relationships with `lazy="selectin"`, so any `Bot` fetch triggers 9 secondary queries even for endpoints that only need the core columns.
- Files: `app/models/bot.py` lines 119–168
- Cause: Same blanket `lazy="selectin"` strategy.
- Improvement path: Switch to `lazy="raise"` + explicit `selectinload` per query.

**In-process vector scan for semantic cache blocks event loop:**
- Problem: As noted under tech debt, `SemanticCompletionCache.lookup()` in `app/services/semantic_completion_cache.py` runs a Python `for` loop over up to 200 entries during an `async` chat handler. Python GIL notwithstanding, this is synchronous CPU work inside an `async` method.
- Files: `app/services/semantic_completion_cache.py` lines 142–210
- Cause: No off-process ANN index; all similarity is computed in-process.
- Improvement path: Wrap the vector scan in `asyncio.to_thread()` as a short-term fix; migrate to pgvector or RediSearch ANN long-term.

**Database connection pool uses SQLAlchemy defaults (no explicit sizing):**
- Problem: `app/core/db.py` creates the async engine with no explicit `pool_size` or `max_overflow`. SQLAlchemy async defaults are 5 connections + 10 overflow. Under concurrent Telegram/widget traffic this can exhaust quickly.
- Files: `app/core/db.py` lines 31–36
- Cause: Pool configuration was not added to `Settings`.
- Improvement path: Add `APP_DB_POOL_SIZE` and `APP_DB_MAX_OVERFLOW` settings; set `pool_size=20, max_overflow=10` at minimum for production.

**Email campaign sends loop serially without concurrency:**
- Problem: `app/api/v1/admin_campaigns.py` `_send_campaign_emails()` iterates recipients in a synchronous `for` loop, sending each email with `await client.send(...)` before moving to the next. For large recipient lists, this is purely serial.
- Files: `app/api/v1/admin_campaigns.py` lines 303–313
- Cause: Background task fires without concurrency limiting or batching.
- Improvement path: Use `asyncio.gather` with a semaphore to send in parallel batches.

---

## Fragile Areas

**Knowledge ingestion worker is a standalone process with a single Redis list:**
- Files: `app/workers/knowledge_ingestion_worker.py`, `app/core/knowledge_ingestion_queue.py`
- Why fragile: Uses a Redis `LPUSH/BRPOP` list with no dead-letter topic visibility, no message acknowledgment, and no per-item lock. If the worker crashes mid-processing after BRPOP but before completing DB writes, the item is permanently lost (not requeued).
- Safe modification: Always update `ingestion_failure_count` before committing any side effects; extend the retry logic to handle the "BRPOP + crash" lost-message scenario by tracking in-flight items.
- Test coverage: `tests/test_knowledge_ingestion_integration.py` covers successful and retry paths but not the crash-mid-processing scenario.

**`knowledge_ingestion_queue.py` uses an uncoupled module-level Redis singleton:**
- Files: `app/core/knowledge_ingestion_queue.py` lines 23–47
- Why fragile: `_redis_client` and `_redis_url_bound` are module globals with no thread/coroutine safety. Under concurrent async calls, the `if _redis_client is not None and _redis_url_bound == url` check is a TOCTOU race.
- Safe modification: Use an `asyncio.Lock` to guard the initialization path (same pattern as the rate limiter).
- Test coverage: `reset_knowledge_ingestion_redis_client_for_tests()` exists but tests do not exercise concurrent re-initialization.

**`SalesConversationOrchestrator` internal JSON keys are opaque strings:**
- Files: `app/services/sales_conversation_orchestrator.py` (docstring lists `__orch_target_field`, `_qp_clar_round`, `__lead_capture_done`, etc.)
- Why fragile: Private orchestrator keys stored in `collected_data_json` JSONB are string constants scattered throughout the file. Any key rename or typo silently produces a state machine failure at runtime.
- Safe modification: Define all internal keys as module-level constants; add a schema validator on `collected_data_json` read paths.
- Test coverage: `tests/test_sales_conversation_orchestrator.py` covers transitions but not key-collision edge cases.

**`admin_campaigns` background task opens its own DB session outside DI:**
- Files: `app/api/v1/admin_campaigns.py` lines 293–317
- Why fragile: `_send_campaign_emails()` calls `get_session_maker()` directly inside a background task, bypassing FastAPI's dependency injection and the request-scoped DB session. Session lifecycle is not tied to the task outcome; `# type: ignore[attr-defined]` suppression indicates the type checker does not validate the session factory call.
- Safe modification: Use a dedicated repository dependency or pass the session factory via dependency injection. Consider a proper background worker (Celery, ARQ) for campaign sends.
- Test coverage: No dedicated unit test for the background session path.

**In-memory rate limiter shared across all async requests (single asyncio.Lock):**
- Files: `app/core/limiters/memory_sliding_window.py`
- Why fragile: `InMemorySlidingWindowLimiter._lock` is a single `asyncio.Lock`. Under high throughput, all rate-limited endpoints serialize through one lock per limiter instance.
- Safe modification: Switch to per-key locks or a lockless approach (e.g., per-key deque with `collections.deque`).

---

## Scaling Limits

**Knowledge chunk vector similarity: O(N) in-process per chat turn:**
- Current capacity: 200 entries per bot before the scan becomes noticeable (< 5 ms). At 500 bots active simultaneously, 200 × 500 float comparisons run during request handling.
- Limit: Degrades noticeably around 50+ concurrent active bots with full caches.
- Scaling path: Migrate to pgvector ANN or RediSearch; see tech debt item above.

**Redis rate-limit keys are all scoped to a single Redis instance:**
- Current capacity: Single Redis URL (`rate_limit_redis_url`). Knowledge ingestion, rate limiting, semantic cache, sales LLM burst, and widget abuse tracking all share one connection pool.
- Limit: If Redis becomes a bottleneck, there is no sharding or read-replica strategy.
- Scaling path: Separate `knowledge_ingestion_redis_url` and `ai_semantic_cache_redis_url` are already available as config; ensure all high-throughput paths use dedicated URLs.

**Conversation history is loaded in full per chat turn:**
- Current capacity: `app/repositories/ai_chat_repository.py` loads recent history; no pagination on deep conversations.
- Limit: Very long conversations (hundreds of turns) cause proportionally larger DB reads and larger prompt tokens.
- Scaling path: Enforce a hard `history_turns_limit` per turn; add prompt-compression for older messages.

---

## Dependencies at Risk

**`stripe` is an optional, lazy-imported dependency:**
- Risk: `stripe` is not listed as a required dependency — it is `import stripe` with `# type: ignore`. If the billing feature is deployed but `stripe` is missing from `requirements.txt` or `pyproject.toml`, billing fails silently at first call.
- Impact: Checkout sessions, portal sessions, and webhook handling all raise `StripeNotConfiguredError` at runtime.
- Migration plan: Add `stripe` as a required dependency (not optional), or add a startup check that imports it when `stripe_secret_key` is configured.

**`resend` is a lazy optional import:**
- Risk: `app/integrations/email/resend_client.py` imports `resend` lazily (`import resend  # lazy import so app starts without resend installed`). If resend is not installed and email verification or password reset is triggered, the call silently returns `False`.
- Impact: Users cannot receive verification or password-reset emails.
- Migration plan: Add `resend` to required dependencies or add a startup check.

**`pdfminer.six` / PDF extraction library:**
- Risk: `app/workers/knowledge_pdf_processing.py` and `app/services/knowledge_pdf_text_extraction.py` depend on PDF extraction. If the library version produces different text extraction output (e.g., on library upgrade), chunk content changes silently, invalidating all existing FTS indices without re-ingestion.
- Impact: Stale FTS results until all files are re-ingested.
- Migration plan: Pin the PDF extraction library version; add a version check to the ingestion worker startup.

---

## Missing Critical Features

**No pgvector semantic retrieval for knowledge RAG:**
- Problem: Chat answers from knowledge files rely on FTS keyword matching. Users asking "what are your refund policies?" may miss chunks that contain "money-back guarantee" because synonym lookup is not supported by FTS `simple` config.
- Blocks: High-quality RAG for non-trivial queries; multi-language retrieval.

**No background job infrastructure for email campaigns (uses FastAPI `BackgroundTasks`):**
- Problem: `admin_campaigns._send_campaign_emails` uses FastAPI's `BackgroundTasks`, which runs in the same process and has no retry, no visibility, no persistence on crash. A restart mid-campaign loses send progress.
- Blocks: Reliable bulk email campaigns.

**No Stripe subscription period tracking in DB:**
- Problem: `app/services/billing_service.py` `_on_checkout_completed` passes `current_period_start=None` and `current_period_end=None` to `upsert_from_stripe`. Period boundaries are not stored, so the app cannot reason about subscription expiry without querying Stripe directly.
- Blocks: Grace period enforcement; local cache of billing state.

---

## Test Coverage Gaps

**`_send_campaign_emails` background task:**
- What's not tested: The code path where the background DB session is opened inside `_send_campaign_emails` (the `async_session_factory` call). Tests for `admin_campaigns` use mocked or integration setups that do not exercise the background session lifecycle or failure scenarios.
- Files: `app/api/v1/admin_campaigns.py` lines 293–331
- Risk: Session leak or silent status-update failure goes unnoticed.
- Priority: Medium

**Stripe webhook duplicate-event handling without Redis:**
- What's not tested: The path where `billing_service.handle_stripe_webhook` is called with `redis=None`. The idempotency guard is skipped entirely; no test verifies that replayed events without Redis cause double-activation.
- Files: `app/services/billing_service.py` lines 284–289
- Risk: Double subscription activation on Stripe retry.
- Priority: High

**Knowledge ingestion worker crash-mid-processing (lost message):**
- What's not tested: Scenario where the worker calls `BRPOP` and receives a file_id but crashes before the DB write. The message is consumed from Redis and never retried.
- Files: `app/workers/knowledge_ingestion_worker.py`, `app/core/knowledge_ingestion_queue.py`
- Risk: Silent knowledge file stuck in `uploaded` state with no retry.
- Priority: Medium

**`SemanticCompletionCache` concurrent re-initialization race:**
- What's not tested: Two coroutines calling `_shared_async_redis()` simultaneously when `_redis_client is None`.
- Files: `app/core/knowledge_ingestion_queue.py`
- Risk: Duplicate Redis client connections under high concurrency.
- Priority: Low

**Multi-worker in-memory rate limiter bypass:**
- What's not tested: The scenario where `RATE_LIMIT_REDIS_URL` is absent and two uvicorn workers each maintain independent counters, effectively doubling the rate limit.
- Files: `app/core/limiters/memory_sliding_window.py`
- Risk: Rate limit bypass in production without Redis.
- Priority: High

---

*Concerns audit: 2026-05-30*
