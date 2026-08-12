# Codebase Structure

**Analysis Date:** 2026-05-30

## Directory Layout

```
botforge_ai/
├── main.py                     # ASGI entrypoint (uvicorn main:app)
├── pyproject.toml              # Python project metadata and tool config
├── requirements.txt            # Pinned dependencies
├── pytest.ini                  # Test runner configuration
├── alembic.ini                 # Alembic migration config
├── Dockerfile                  # Production container image
├── docker-compose.yml          # Local dev stack (API + DB + Redis)
│
├── app/                        # Python application package
│   ├── main.py                 # FastAPI app factory (create_app)
│   ├── api/                    # HTTP layer
│   │   ├── deps.py             # FastAPI Depends factory functions (DI wiring)
│   │   ├── router.py           # Aggregated api_router (all v1 routes)
│   │   ├── auth_csrf.py        # CSRF enforcement dependency
│   │   ├── auth_http.py        # Bearer token resolution
│   │   └── v1/                 # One file per resource group
│   │       ├── auth.py         # /api/v1/auth/*
│   │       ├── bots.py         # /api/v1/bots
│   │       ├── bot_chat.py     # /api/v1/bots/{id}/chat/*
│   │       ├── bot_knowledge_files.py
│   │       ├── bot_knowledge_retrieval.py
│   │       ├── bot_telegram.py
│   │       ├── bot_widget.py
│   │       ├── billing.py
│   │       ├── analytics.py
│   │       ├── leads.py
│   │       ├── public_widget.py    # /api/v1/public/widget/* (unauthenticated)
│   │       ├── public_telegram.py  # /api/v1/telegram/webhook/* (Telegram)
│   │       ├── google_oauth.py
│   │       ├── github_oauth.py
│   │       ├── oauth_exchange.py
│   │       ├── niche_catalog.py
│   │       ├── support.py
│   │       ├── health.py
│   │       └── admin_*.py          # Superadmin-only endpoints (15 files)
│   │
│   ├── core/                   # Shared infrastructure (no business logic)
│   │   ├── config.py           # pydantic-settings Settings class + get_settings()
│   │   ├── db.py               # Async SQLAlchemy engine + get_db()
│   │   ├── redis_client.py     # Shared async Redis connection
│   │   ├── logging.py          # structlog configuration
│   │   ├── middleware.py       # RequestLoggingMiddleware
│   │   ├── security_headers.py # SecurityHeadersMiddleware
│   │   ├── exception_handlers.py # Global domain exception → HTTP mapping
│   │   ├── exceptions.py       # Base infrastructure exceptions
│   │   ├── error_response.py   # StandardErrorResponse schema
│   │   ├── error_tracking.py   # Sentry integration wrapper
│   │   ├── rbac.py             # Role/capability checks
│   │   ├── rate_limit.py       # Rate limit helpers
│   │   ├── auth_cookies.py     # HttpOnly cookie read/write
│   │   ├── auth_audit.py       # Auth event logging
│   │   ├── ai_generation_policy.py     # Token cap enforcement
│   │   ├── ai_pipeline_observability.py # AI pipeline metrics/logging
│   │   ├── knowledge_ingestion_pipeline.py # Ingestion outcome handler
│   │   ├── knowledge_ingestion_queue.py    # Redis queue wrapper
│   │   ├── public_widget_abuse.py          # Widget abuse heuristics
│   │   ├── widget_abuse_redis.py           # Redis streak tracker
│   │   ├── public_widget_channel_events.py # Widget analytics events
│   │   ├── telegram_channel_events.py      # Telegram analytics events
│   │   ├── security/           # JWT + password utilities
│   │   │   ├── jwt_tokens.py
│   │   │   ├── passwords.py
│   │   │   └── token_errors.py
│   │   └── limiters/           # Rate limiter implementations
│   │       ├── protocol.py     # SlidingWindowLimiterPort (Protocol)
│   │       ├── factory.py      # Select memory vs Redis limiter at startup
│   │       ├── memory_sliding_window.py
│   │       └── redis_sliding_window.py
│   │
│   ├── services/               # Business logic layer (~60 files)
│   │   ├── ai_service.py       # Core AI orchestration
│   │   ├── sales_conversation_orchestrator.py
│   │   ├── auth_service.py
│   │   ├── bot_service.py
│   │   ├── billing_service.py
│   │   ├── plan_limits.py      # Static plan catalogue
│   │   ├── public_widget_chat_service.py
│   │   ├── telegram_webhook_inbound_service.py
│   │   ├── telegram_config_service.py
│   │   ├── bot_knowledge_file_service.py
│   │   ├── knowledge_file_processing_service.py
│   │   ├── knowledge_retrieval_service.py
│   │   ├── lead_pipeline_service.py
│   │   ├── lead_creation_service.py
│   │   ├── lead_owner_delivery_router.py
│   │   ├── conversation_state_machine.py
│   │   ├── intent_classifier_service.py
│   │   ├── intent_rule_engine.py
│   │   ├── question_planner.py
│   │   ├── response_planner.py
│   │   ├── ai_usage_log_service.py
│   │   ├── ai_usage_quota_service.py
│   │   ├── *_exceptions.py     # Domain exception classes (one per domain)
│   │   └── ...                 # ~40 more service files
│   │
│   ├── repositories/           # DB access layer (~20 files)
│   │   ├── bot_repository.py
│   │   ├── ai_chat_repository.py
│   │   ├── user_repository.py
│   │   ├── lead_repository.py
│   │   ├── knowledge_file_repository.py
│   │   ├── knowledge_chunk_repository.py
│   │   ├── knowledge_retrieval_repository.py
│   │   ├── subscription_repository.py
│   │   ├── refresh_session_repository.py
│   │   └── ...                 # ~12 more repository files
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── base.py             # DeclarativeBase
│   │   ├── enums.py            # UserRole, PlanSlug, SubscriptionStatus, OAuthProvider
│   │   ├── user.py
│   │   ├── bot.py              # Bot aggregate root
│   │   ├── ai_foundation.py    # Conversation, AIMessage, AIUsageLog, AIUsageAggregate
│   │   ├── conversation_flow.py # ConversationFlowState enum + check constraints
│   │   ├── lead.py
│   │   ├── lead_event.py
│   │   ├── subscription.py
│   │   ├── knowledge_file.py
│   │   ├── knowledge_chunk.py
│   │   ├── telegram_config.py
│   │   ├── widget_config.py
│   │   ├── refresh_session.py
│   │   ├── audit_log.py
│   │   ├── feature_flag.py
│   │   ├── coupon.py
│   │   ├── email_campaign.py
│   │   ├── support_ticket.py
│   │   └── webhook_log.py
│   │
│   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── ai_chat.py
│   │   ├── ai_usage.py
│   │   ├── auth.py
│   │   ├── bots.py
│   │   ├── lead.py
│   │   ├── public_widget_chat.py
│   │   ├── widget_config.py
│   │   ├── knowledge_file.py
│   │   ├── knowledge_retrieval.py
│   │   └── ...                 # ~15 more schema files
│   │
│   ├── ai_providers/           # LLM provider abstraction
│   │   ├── base.py             # AIProvider ABC
│   │   ├── registry.py         # provider_id → factory
│   │   ├── types.py            # GenerateParams, NormalizedAIResult, ChatMessage, TokenUsage
│   │   ├── exceptions.py       # Provider-level errors
│   │   └── gemini.py           # Thin re-export (implementation in integrations/)
│   │
│   ├── ai_cost/                # Token normalization + USD pricing
│   │   ├── __init__.py         # Public API re-exports
│   │   ├── calculator.py       # normalize_usage, calculate_cost, estimate_tokens_from_messages
│   │   ├── catalog.py          # build_pricing_catalog + APP_AI_PRICING_JSON overlay
│   │   └── types.py            # CostBreakdown
│   │
│   ├── prompting/              # System prompt assembly
│   │   ├── builder.py          # build_chat_prompt / build_prompt_package
│   │   ├── types.py            # PromptBuildInput, PromptExtensionContext, HistoryTurn, PromptPackage
│   │   ├── adapters.py         # bot_to_prompt_source (Bot ORM → BotPromptSource)
│   │   ├── smart_system.py     # LRU-cached identity + tone blocks
│   │   ├── history.py          # truncate_history_turns
│   │   ├── history_clean.py    # clean_history_for_prompt
│   │   ├── knowledge_excerpt.py # format_knowledge_context_excerpt (RAG injection)
│   │   ├── slimming.py         # prompt_build_options_for_user_text (compact mode)
│   │   ├── safety.py           # scrub_secrets_for_prompt
│   │   ├── style.py            # Full warm-tone style guide
│   │   └── compact_tone.py     # Compact tone variant
│   │
│   ├── lib/                    # Pure-logic helpers (no DB/service imports)
│   │   ├── niche_flow/         # Per-industry sales conversation definitions
│   │   │   ├── registry.py     # get_niche_conversation_flow_or_generic()
│   │   │   ├── schema.py       # NicheConversationFlowDefinition
│   │   │   ├── education.py
│   │   │   ├── healthcare.py
│   │   │   ├── dev_agency.py
│   │   │   ├── services.py
│   │   │   ├── planner_hooks.py
│   │   │   └── validation.py
│   │   ├── niche_registry.py   # Niche catalog (get_niche_by_id)
│   │   ├── chat_channels.py    # Channel constant strings
│   │   ├── widget_origin_policy.py
│   │   ├── widget_allowed_domains.py
│   │   ├── public_widget_key.py
│   │   ├── platform_moderation.py
│   │   ├── telegram_token_crypto.py
│   │   ├── integration_secrets_crypto.py
│   │   ├── refresh_token_hash.py
│   │   ├── email_normalize.py
│   │   ├── vector_cosine.py
│   │   └── web_widget_visitor_session.py
│   │
│   ├── integrations/           # External service clients
│   │   ├── providers/          # AI provider implementations
│   │   │   ├── gemini.py       # GeminiProvider (httpx-based)
│   │   │   ├── gemini_errors.py
│   │   │   └── gemini_usage.py
│   │   ├── storage/            # S3/MinIO object storage
│   │   │   ├── s3.py
│   │   │   ├── base.py
│   │   │   ├── keys.py
│   │   │   └── read_object.py
│   │   ├── telegram/           # Outbound Telegram alerts
│   │   │   ├── telegram_send.py
│   │   │   ├── lead_alert_message.py
│   │   │   ├── lead_alert_target.py
│   │   │   └── lead_alert_types.py
│   │   ├── telegram_bot_api/   # Telegram Bot API types + parsing
│   │   ├── email/              # Email delivery (Resend)
│   │   │   ├── resend_client.py
│   │   │   └── templates.py
│   │   ├── gemini_text_embedding.py  # Gemini embedContent API (v1)
│   │   ├── oauth_exchange_store.py
│   │   ├── google_idp.py
│   │   ├── github_idp.py
│   │   ├── oauth_redirect.py
│   │   ├── oauth_state.py
│   │   └── telegram_bot_reply.py
│   │
│   ├── contracts/              # Typed interfaces for cross-boundary communication
│   │   ├── lead_owner_delivery.py         # NewLeadDeliveryContext, TelegramChannelAttemptResult
│   │   └── telegram_channel_provisioning.py # TelegramChannelProvisioningPort
│   │
│   ├── domain/                 # Domain constants and status values
│   │   ├── telegram_channel_status.py
│   │   └── telegram_channel_provisioning.py (provisioning port implementation)
│   │
│   └── workers/                # Standalone background processes
│       ├── knowledge_ingestion_worker.py  # BRPOP PDF processing loop
│       └── knowledge_pdf_processing.py    # Per-file PDF pipeline
│
├── alembic/                    # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/               # 31 migration files (5357abad → z9y8x7w6)
│
├── tests/                      # Test suite (flat directory, ~150 test files)
│   ├── conftest.py             # Shared fixtures
│   ├── fixtures/               # Reusable test data
│   ├── integration/            # DB integration fixtures
│   └── test_*.py               # Test files co-located at root of tests/
│
├── frontend/                   # Next.js frontend application
│   └── src/
│       ├── app/                # Next.js App Router pages
│       ├── components/         # React components
│       │   ├── chat/
│       │   ├── dashboard/      # Dashboard sections (bots, billing, analytics, etc.)
│       │   └── ui/             # Primitive UI components
│       ├── lib/                # Frontend utilities (API client, auth, bot domain)
│       ├── hooks/              # React hooks
│       ├── contexts/           # React context providers
│       ├── types/              # TypeScript type definitions
│       └── i18n/               # Internationalization
│
├── embed/                      # Embeddable chat widget
│   └── widget/
│       └── src/                # Widget source (compiled to dist/)
│
├── docs/                       # Project documentation
│   ├── db/                     # DB schema docs
│   ├── deployment/
│   ├── observability/
│   ├── qa/
│   ├── release/
│   └── security/
│
├── scripts/                    # Deployment and utility scripts
│   └── deploy/
│
└── load/                       # Load testing
    └── k6/                     # k6 scripts
```

## Directory Purposes

**`app/api/v1/`:**
- Purpose: HTTP route handlers — thin, delegate to services, never contain business logic
- Contains: One `.py` file per resource group; `admin_*.py` files for superadmin routes
- Key files: `app/api/router.py` (aggregates all routers), `app/api/deps.py` (all DI wiring)

**`app/core/`:**
- Purpose: Shared infrastructure concerns used across all layers
- Contains: Config, DB, Redis, logging, security, middleware, rate limiting, exception handlers
- Key files: `app/core/config.py`, `app/core/db.py`, `app/core/exception_handlers.py`

**`app/services/`:**
- Purpose: All business logic; owns transaction boundaries
- Contains: Use-case classes + domain exception modules
- Key files: `app/services/ai_service.py`, `app/services/sales_conversation_orchestrator.py`, `app/services/auth_service.py`

**`app/repositories/`:**
- Purpose: Owner-scoped database access; no business logic
- Contains: One repository class per ORM model aggregate
- Key files: `app/repositories/ai_chat_repository.py`, `app/repositories/bot_repository.py`

**`app/models/`:**
- Purpose: SQLAlchemy ORM table definitions; source of truth for DB schema shape
- Contains: Declarative model classes + `Base`
- Key files: `app/models/base.py`, `app/models/ai_foundation.py`, `app/models/bot.py`

**`app/schemas/`:**
- Purpose: Pydantic v2 request/response contracts for API handlers
- Contains: Input schemas (request bodies) and output schemas (response models)
- Key files: `app/schemas/ai_chat.py`, `app/schemas/bots.py`, `app/schemas/lead.py`

**`app/ai_providers/`:**
- Purpose: Vendor-neutral LLM abstraction layer
- Contains: `AIProvider` ABC, provider registry, shared types
- Key files: `app/ai_providers/base.py`, `app/ai_providers/registry.py`, `app/ai_providers/types.py`

**`app/prompting/`:**
- Purpose: System prompt assembly, history truncation, RAG context formatting
- Contains: Builder, type definitions, style/tone modules, safety scrubber
- Key files: `app/prompting/builder.py`, `app/prompting/types.py`, `app/prompting/knowledge_excerpt.py`

**`app/lib/`:**
- Purpose: Pure business-logic helpers with no DB or service imports; reusable from anywhere
- Contains: Niche flow definitions, crypto utilities, widget domain logic, vector math
- Key files: `app/lib/niche_flow/registry.py`, `app/lib/niche_registry.py`, `app/lib/chat_channels.py`

**`app/integrations/`:**
- Purpose: All external service clients (HTTP, storage, email)
- Contains: Gemini provider, S3/MinIO client, Resend email, Telegram Bot API, OAuth IDPs
- Key files: `app/integrations/providers/gemini.py`, `app/integrations/storage/s3.py`, `app/integrations/email/resend_client.py`

**`app/ai_cost/`:**
- Purpose: Token usage normalization and USD cost calculation
- Contains: Catalog builder, calculator, types
- Key files: `app/ai_cost/catalog.py`, `app/ai_cost/calculator.py`

**`app/workers/`:**
- Purpose: Standalone async processes that are not part of the FastAPI ASGI app
- Contains: Knowledge ingestion worker (PDF pipeline)
- Key files: `app/workers/knowledge_ingestion_worker.py`

**`alembic/versions/`:**
- Purpose: Database migration history (31 files, sequential)
- Generated: No (written by developers)
- Committed: Yes

**`tests/`:**
- Purpose: Full test suite — unit, integration, and end-to-end
- Contains: Flat `test_*.py` files + `fixtures/` + `integration/` sub-directories
- Key files: `tests/conftest.py`, `tests/integration_db.py`

## Naming Conventions

**Files:**
- Snake_case for all Python modules: `bot_service.py`, `ai_chat_repository.py`
- Resource groups in API layer: `{resource}.py` or `{resource}_{sub-resource}.py` — e.g. `bot_knowledge_files.py`
- Admin endpoints prefixed: `admin_{topic}.py` — e.g. `admin_moderation.py`
- Domain exceptions co-located with service: `{domain}_exceptions.py` — e.g. `auth_exceptions.py`
- Integration clients in `app/integrations/{service}/` — e.g. `app/integrations/email/resend_client.py`

**Directories:**
- Snake_case: `ai_providers/`, `niche_flow/`, `telegram_bot_api/`
- Versioned API: `api/v1/` (v2 would be `api/v2/`)

**Classes:**
- Services: `{Domain}Service` — e.g. `AIService`, `BillingService`
- Repositories: `{Model}Repository` — e.g. `BotRepository`, `AIChatRepository`
- Exceptions: `{SpecificError}Error` — e.g. `InvalidCredentialsError`, `BotLimitExceededError`
- Schemas: PascalCase with `Request`/`Response`/`Read`/`Create` suffixes — e.g. `BotCreateRequest`, `UserRead`

## Key File Locations

**Entry Points:**
- `main.py`: Root uvicorn entry (imports `app.main.app`)
- `app/main.py`: FastAPI `create_app()` factory + lifespan
- `app/api/router.py`: All route registration in one place

**Configuration:**
- `app/core/config.py`: All environment variables documented in `Settings` class
- `pyproject.toml`: Ruff, pytest, and project metadata
- `pytest.ini`: Test configuration (markers, asyncio mode)
- `alembic.ini`: Migration runner config

**Core Logic:**
- `app/services/ai_service.py`: AI chat pipeline orchestration
- `app/services/sales_conversation_orchestrator.py`: Sales funnel state machine
- `app/ai_providers/base.py`: Provider abstraction
- `app/ai_providers/registry.py`: Provider factory registration
- `app/prompting/builder.py`: System prompt assembly

**Testing:**
- `tests/conftest.py`: Shared fixtures (DB session, test client, auth helpers)
- `tests/integration_db.py`: Integration test DB setup

## Where to Add New Code

**New API endpoint:**
1. Create handler in `app/api/v1/{resource}.py` (or add to existing file for same resource)
2. Create service in `app/services/{resource}_service.py`
3. Create repository in `app/repositories/{resource}_repository.py` if new DB table
4. Add Pydantic schemas in `app/schemas/{resource}.py`
5. Register router in `app/api/router.py`
6. Add service/repo factory in `app/api/deps.py`

**New ORM model:**
1. Create `app/models/{name}.py` extending `app/models/base.py:Base`
2. Import in `app/core/db.py` or ensure model is imported before migrations run
3. Generate migration: `alembic revision --autogenerate -m "add_{name}_table"` in `alembic/versions/`

**New AI provider:**
1. Implement `AIProvider` ABC in `app/integrations/providers/{provider}.py`
2. Register with `register_provider_factory("{provider_id}", factory)` in `app/ai_providers/registry.py`

**New niche flow (sales funnel):**
1. Create `app/lib/niche_flow/{niche}.py` with `NicheConversationFlowDefinition`
2. Register in `app/lib/niche_flow/registry.py`
3. Add niche to `app/lib/niche_registry.py`

**New utility (no DB/service deps):**
- Shared logic: `app/lib/{name}.py`

**New test:**
- Unit tests: `tests/test_{module}_unit.py`
- Integration tests: `tests/test_{feature}_integration.py`
- Use existing fixtures from `tests/conftest.py`

## Special Directories

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning documents and codebase maps
- Generated: Yes (by GSD commands)
- Committed: Yes

**`.github/workflows/`:**
- Purpose: CI/CD pipeline definitions
- Generated: No
- Committed: Yes

**`embed/widget/dist/`:**
- Purpose: Compiled embeddable widget JavaScript
- Generated: Yes (from `embed/widget/src/`)
- Committed: Check `.gitignore`

**`embed/widget/node_modules/`:**
- Purpose: Widget npm dependencies
- Generated: Yes
- Committed: No

**`alembic/versions/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No

---

*Structure analysis: 2026-05-30*
