# Database hotspots — analysis and optimization log

This document records **measured** query paths called out in performance review, what the planner needs, and what we changed. Re-run `EXPLAIN (ANALYZE, BUFFERS)` on **staging** after schema changes; numbers below are qualitative unless you paste real timings.

## 1. Lead list (`GET /api/v1/leads`)

**Path:** `LeadRepository._build_owner_list_stmt` → `ORDER BY leads.updated_at DESC` + optional filters (`status`, `niche_id`, `bot_id`, `lead_temperature`).

**Before:** B-tree `ix_leads_owner_id_created_at (owner_id, created_at)` did not match the sort key (`updated_at`). For large inboxes, PostgreSQL tended toward **filter by owner → sort** (external sort) or suboptimal index-only paths.

**After:** `ix_leads_owner_id_updated_at (owner_id, updated_at DESC NULLS LAST)` aligns the index with the default CRM ordering.

**EXPLAIN template (staging):**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM leads
WHERE owner_id = '<uuid>'
ORDER BY updated_at DESC
LIMIT 50 OFFSET 0;
```

**Acceptance:** plan uses **Index Scan** (or index scan + filter) on `ix_leads_owner_id_updated_at`, avoiding a large **Sort** on `updated_at`.

**Not changed (yet):** heavy use of **optional equality filters** (e.g. `status` + sort) may still prefer a dedicated composite `(owner_id, status, updated_at DESC)` — add only if profiling shows it.

**Related:** `lead_events` timeline already has `ix_lead_events_lead_id_created_at`.

---

## 2. Knowledge retrieval (`POST .../knowledge/retrieve`)

**Path:** `KnowledgeRetrievalRepository.search_full_text` — `knowledge_chunks` joined to `knowledge_files`, filter `owner_id`, `bot_id`, `processing_status = 'ready'`, `to_tsvector('simple', content) @@ websearch_to_tsquery(...)`, `ORDER BY ts_rank(...)`.

**Indexes in place:**

- `ix_knowledge_chunks_content_fts` — GIN on `to_tsvector('simple', content)` (migration `p6q7r8s9t0u1`).
- `ix_knowledge_chunks_owner_id_bot_id` — narrows chunks per bot.

**EXPLAIN template:**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ... -- paste generated SQL from logs or echo the statement in dev
```

**Acceptance:** GIN bitmap / index scan on FTS plus heap fetches bounded by `LIMIT`; no full sequential scan on `knowledge_chunks` for typical bot corpora.

**Not changed:** no query rewrite in this pass; FTS + join shape was already aligned with existing indexes.

---

## 3. Superadmin lists (`/api/v1/admin/users`, `/api/v1/admin/bots`)

**Users — before:** `list_users_with_counts` used **correlated scalar subqueries** for bot and OAuth counts (effectively per-row subplans).

**Users — after:** single pass **outer join** to grouped subqueries on `bots.owner_id` and `oauth_accounts.user_id`. Reduces repeated sequential scans over `bots` / `oauth_accounts` for each row in the user page.

**Users — index:** `ix_users_created_at (created_at DESC NULLS LAST)` supports `ORDER BY users.created_at DESC` on full user listings.

**Bots — before:** `ORDER BY bots.updated_at DESC` for global listing; only `ix_bots_owner_id_updated_at` existed (per-owner), not global recency.

**Bots — after:** `ix_bots_updated_at (updated_at DESC NULLS LAST)`.

**EXPLAIN templates:**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM users ORDER BY created_at DESC LIMIT 50;

EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bots ORDER BY updated_at DESC LIMIT 50;
```

---

## 4. Other dashboard / high-frequency paths (inventory)

| Area | Query pattern | Existing index / note |
|------|----------------|------------------------|
| AI usage rollups | `DailyAIUsageAggregate` + `Bot.owner_id` + date range | Review when aggregate table grows |
| Recent AI failures | `AIUsageLog` join `Bot` filter `owner_id`, `success = false`, order `created_at` | `ix_ai_usage_logs_bot_id_created_at` |
| Conversations by owner | `Conversation.owner_id` | `ix_conversations_owner_id` |

No changes here in this iteration — **no evidence** of regression; revisit with `pg_stat_statements` or APM.

---

## 5. Migration

Apply with Alembic:

`alembic/versions/d0e1f2a3b4c5_add_listing_perf_indexes.py`

---

## 6. Benchmark notes

1. Run `EXPLAIN (ANALYZE, BUFFERS)` on the statements above **before** and **after** migration on a DB with **realistic row counts** (or restored prod snapshot).
2. Prefer comparing: **execution time**, **shared hit ratio**, **whether Sort/HashAggregate nodes disappear** for lead and admin lists.
3. Optional: enable `pg_stat_statements`, reset, run a short load test (e.g. k6 dashboard flows), compare top queries by `total_exec_time`.

**Write capacity:** three new secondary indexes add modest INSERT/UPDATE cost on `leads`, `users`, and `bots`; acceptable for the read-heavy dashboard/admin paths targeted here.
