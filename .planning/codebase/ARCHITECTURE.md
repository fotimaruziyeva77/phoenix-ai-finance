<!-- refreshed: 2026-05-30 -->
# Architecture

**Analysis Date:** 2026-05-30

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HTTP Layer (FastAPI / Starlette)                      │
│  RequestLoggingMiddleware · SecurityHeadersMiddleware · CORSMiddleware       │
│  SlidingWindowRateLimiter · ExceptionHandlers                                │
├───────────────────┬────────────────────┬───────────────────┬────────────────┤
│  app/api/v1/      │  app/api/v1/       │  app/api/v1/      │ app/api/v1/    │
│  auth*.py         │  bots*.py          │  public_widget.py │ public_        │
│  google/github    │  bot_chat.py       │  bot_widget.py    │ telegram.py    │
│  _oauth*.py       │  bot_knowledge*.py │                   │                │
└───────┬───────────┴──────────┬─────────┴────────┬──────────┴────────┬───────┘
        │                      │                   │                   │
        ▼                      ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
│  app/services/                                                               │
│  AuthService · BotService · AIService · SalesConversationOrchestrator       │
│  PublicWidgetChatService · TelegramWebhookInboundService                    │
│  BillingService · KnowledgeFileProcessingService · LeadPipelineService      │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────┐
        ▼                               ▼                       ▼
┌──────────────────┐   ┌───────────────────────────┐   ┌──────────────────┐
│  Repository Layer│   │   AI Pipeline              │   │  External        │
│  app/repositories│   │   app/ai_providers/        │   │  Integrations    │
│  BotRepository   │   │   AIProvider (abstract)    │   │  app/integrations│
│  AIChatRepository│   │   GeminiProvider           │   │  Gemini API      │
│  LeadRepository  │   │   app/prompting/           │   │  Stripe          │
│  UserRepository  │   │   app/ai_cost/             │   │  Resend Email    │
│  (20+ repos)     │   │   app/lib/niche_flow/      │   │  S3/MinIO        │
└────────┬─────────┘   └───────────────────────────┘   │  Telegram Bot API│
         │                                              └──────────────────┘
         ▼
┌────────────────────────────────────────────────────────────┐
│  Persistence Layer                                          │
│  PostgreSQL (asyncpg) · Redis (rate-limits, queues, cache)  │
│  app/models/ (SQLAlchemy ORM)                               │
│  alembic/ (31 migrations)                                   │
└────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | ASGI entrypoint, middleware stack, lifespan | `app/main.py` |
| API Router | Version-prefixed route aggregation | `app/api/router.py` |
| API v1 handlers | Thin HTTP handlers; delegate to services | `app/api/v1/*.py` |
| Dependency injection | Session, auth, service construction | `app/api/deps.py` |
| Settings | Single `pydantic-settings` config object | `app/core/config.py` |
| DB session | Async SQLAlchemy engine + session factory | `app/core/db.py` |
| Redis client | Shared async Redis connection | `app/core/redis_client.py` |
| AuthService | Register, login, refresh, OAuth resolution | `app/services/auth_service.py` |
| BotService | Bot CRUD and status transitions | `app/services/bot_service.py` |
| AIService | Core AI orchestration; RAG + usage logging | `app/services/ai_service.py` |
| SalesConversationOrchestrator | Sales funnel state machine + lead capture | `app/services/sales_conversation_orchestrator.py` |
| PublicWidgetChatService | Unauthenticated widget chat path | `app/services/public_widget_chat_service.py` |
| TelegramWebhookInboundService | Telegram update → AIService → Bot API reply | `app/services/telegram_webhook_inbound_service.py` |
| BillingService | Stripe subscriptions + plan enforcement | `app/services/billing_service.py` |
| KnowledgeFileProcessingService | PDF upload, chunking, embedding | `app/services/knowledge_file_processing_service.py` |
| LeadPipelineService | CRM lead creation, events, routing | `app/services/lead_pipeline_service.py` |
| AIProvider (abstract) | Vendor-neutral LLM completion contract | `app/ai_providers/base.py` |
| GeminiProvider | Google Gemini HTTP implementation | `app/integrations/providers/gemini.py` |
| Provider registry | `provider_id → AIProvider` factory | `app/ai_providers/registry.py` |
| Repositories (20+) | Owner-scoped DB access patterns | `app/repositories/*.py` |
| ORM models | SQLAlchemy declarative models | `app/models/*.py` |
| Prompting system | System prompt assembly + RAG formatting | `app/prompting/*.py` |
| AI cost | Token normalization + USD pricing catalog | `app/ai_cost/` |
| Niche flow | Per-industry sales conversation definitions | `app/lib/niche_flow/` |
| Knowledge worker | Standalone BRPOP PDF ingestion process | `app/workers/knowledge_ingestion_worker.py` |

## Pattern Overview

**Overall:** Layered architecture — HTTP → Service → Repository → ORM/DB — with a provider-abstracted AI pipeline and a sales-specific state-machine sub-system.

**Key Characteristics:**
- Handlers are thin: every API handler delegates immediately to an injected service; no business logic in `app/api/v1/`.
- Services own business logic and transaction boundaries; they receive repositories via constructor injection (not `Depends` directly).
- Repositories are always owner-scoped: every query filters by `owner_id` unless explicitly in an `admin_*` repository method.
- The AI pipeline is provider-agnostic: `AIProvider` abstract base, `resolve_ai_provider()` factory, only `GeminiProvider` registered today; new vendors add a factory registration without touching `AIService`.
- Exception-to-HTTP mapping is centralized: domain exceptions (`AuthServiceError`, `BillingError`, `AIServiceHTTPError`, etc.) are caught by registered handlers in `app/core/exception_handlers.py`, never in route handlers.

## Layers

**HTTP Layer:**
- Purpose: Request parsing, auth middleware, rate limiting, CORS, response serialization
- Location: `app/api/`
- Contains: Route handlers, `Depends` factory functions, middleware classes
- Depends on: Service layer, `app/core/config.py`, `app/core/security/`
- Used by: External HTTP clients (browser, Telegram Bot API, embeddable widget)

**Service Layer:**
- Purpose: Business logic, transaction control, cross-cutting orchestration
- Location: `app/services/`
- Contains: Use-case classes (e.g. `AIService`, `AuthService`), domain exceptions
- Depends on: Repository layer, `app/ai_providers/`, `app/prompting/`, `app/integrations/`
- Used by: API handlers (via `app/api/deps.py`)

**Repository Layer:**
- Purpose: Owner-scoped database access patterns; no business logic
- Location: `app/repositories/`
- Contains: One class per aggregate root; async SQLAlchemy queries
- Depends on: `app/models/` (ORM), `sqlalchemy.ext.asyncio.AsyncSession`
- Used by: Service layer

**AI Pipeline (cross-cutting):**
- Purpose: LLM prompt assembly → provider call → token accounting → caching
- Location: `app/ai_providers/`, `app/prompting/`, `app/ai_cost/`, `app/services/ai_service.py`
- Contains: `AIProvider` ABC, `GeminiProvider`, prompt builder, RAG context selector, cost catalog
- Depends on: `app/integrations/providers/gemini.py`, `app/lib/niche_flow/`
- Used by: `AIService`, `SalesConversationOrchestrator`

**Infrastructure / Core:**
- Purpose: Shared cross-cutting concerns: config, DB, Redis, security, logging, rate limiting
- Location: `app/core/`
- Contains: `Settings`, `get_db()`, JWT utilities, RBAC helpers, sliding-window limiters, structured logging
- Depends on: External: PostgreSQL, Redis, Sentry
- Used by: All layers

**Lib / Utilities:**
- Purpose: Pure-logic helpers with no service or DB imports
- Location: `app/lib/`
- Contains: `niche_flow/` (sales conversation definitions), `niche_registry.py`, crypto helpers, widget key utilities
- Depends on: Nothing in `app/services/` or `app/repositories/`

**Domain / Contracts:**
- Purpose: Shared typed interfaces for cross-boundary communication
- Location: `app/contracts/`, `app/domain/`
- Contains: `LeadOwnerDeliveryPort`, `TelegramChannelProvisioningPort`, channel status constants

**Models:**
- Purpose: SQLAlchemy ORM table definitions
- Location: `app/models/`
- Contains: `Base`, `User`, `Bot`, `Conversation`, `AIMessage`, `AIUsageLog`, `Lead`, `Subscription`, `TelegramConfig`, `WidgetConfig`, `KnowledgeFile`, `KnowledgeChunk`, etc.

**Workers:**
- Purpose: Standalone background processes (not part of the FastAPI ASGI app)
- Location: `app/workers/`
- Contains: `knowledge_ingestion_worker.py` — BRPOP Redis queue consumer for PDF processing
- Entry: `python -m app.workers.knowledge_ingestion_worker`

## Data Flow

### Dashboard Bot Chat (Authenticated)

1. `POST /api/v1/bots/{bot_id}/chat/test` — route handler in `app/api/v1/bot_chat.py`
2. `CurrentUser` dep resolves JWT/cookie, loads `User` from DB (`app/api/deps.py`)
3. Handler calls `BotChatTestService.send_test_message(...)` (`app/services/bot_chat_test_service.py`)
4. Delegates to `AIService.send_bot_message(...)` (`app/services/ai_service.py`)
5. `AIService` checks exact-match cache (Redis), semantic cache (Redis + Gemini embeddings), trivial greeting fast-path
6. On cache miss: `build_chat_prompt(...)` (`app/prompting/builder.py`) assembles system prompt + history
7. Optional RAG: `KnowledgeRetrievalService` fetches relevant `KnowledgeChunk` rows, `format_knowledge_context_excerpt` injects them
8. `resolve_ai_provider(settings, provider_id)` returns `GeminiProvider` (`app/ai_providers/registry.py`)
9. `GeminiProvider.generate_response(params)` calls Gemini REST API (`app/integrations/providers/gemini.py`)
10. `AIService` writes `AIMessage` (assistant) + `AIUsageLog` to DB, returns `SendBotMessageResult`

### Public Widget Chat (Unauthenticated)

1. `POST /api/v1/public/widget/{key}/chat` — `app/api/v1/public_widget.py`
2. Rate limit dep + abuse detection dep run first (`app/api/deps.py`)
3. `PublicWidgetChatService.chat(...)` (`app/services/public_widget_chat_service.py`)
4. `enforce_public_widget_origin_and_enabled()` validates domain allowlist
5. `WebWidgetSessionService` resolves or creates `Conversation` (channel=`web_widget`)
6. Same `AIService` path as dashboard chat (step 5–10 above)

### Telegram Inbound Webhook

1. `POST /api/v1/telegram/webhook/{bot_id}` — `app/api/v1/public_telegram.py`
2. Secret token verification (`app/integrations/telegram_bot_verify.py`)
3. `TelegramWebhookInboundService.handle_update(...)` (`app/services/telegram_webhook_inbound_service.py`)
4. `ConversationThreadService` resolves `Conversation` (channel=`telegram`, `telegram_chat_id`)
5. Same `AIService` path; channel is `telegram`
6. Response sent via `send_telegram_text_to_chat(...)` (`app/integrations/telegram_bot_reply.py`)

### Sales Conversation (goal_type=sales sub-path inside AIService)

1. `AIService.send_bot_message` detects `goal_type=sales` → delegates to `SalesConversationOrchestrator`
2. Orchestrator classifies intent (`IntentClassifierService` + rule engine + optional Gemini classifier)
3. Niche flow registry provides `NicheConversationFlowDefinition` (`app/lib/niche_flow/registry.py`)
4. `ConversationStateMachine.transition(...)` advances `ConversationFlowState`
5. `QuestionPlanner` + `ResponsePlanner` determine next question and prompt extensions
6. Lead capture gate: if qualified, `LeadPipelineService.create_lead(...)` — post-commit
7. `LeadOwnerDeliveryRouter` dispatches to Telegram alert + dashboard stamp

### Knowledge PDF Ingestion (async, standalone process)

1. Bot owner uploads PDF via `POST /api/v1/bots/{bot_id}/knowledge-files` — `app/api/v1/bot_knowledge_files.py`
2. `BotKnowledgeFileService` stores file to S3/MinIO (`app/integrations/storage/s3.py`), enqueues job to Redis list
3. `knowledge_ingestion_worker` BRPOP-loops (`app/workers/knowledge_ingestion_worker.py`)
4. `process_knowledge_file_standalone(...)` extracts PDF text (`app/services/knowledge_pdf_text_extraction.py`)
5. `KnowledgeTextChunking` splits text, chunks stored as `KnowledgeChunk` rows with embeddings

**State Management:**
- No in-process mutable global state per request; each request gets its own `AsyncSession` from the session factory.
- Module-level singletons: `_engine` / `_session_maker` in `app/core/db.py` (lazy-init, disposed on shutdown); `Settings` via `@lru_cache` in `app/core/config.py`; Redis client in `app/core/redis_client.py`.
- Widget streak tracker stored on `app.state.widget_streak_tracker` (set in lifespan).

## Key Abstractions

**AIProvider:**
- Purpose: Vendor-neutral LLM completion interface
- Examples: `app/ai_providers/base.py` (ABC), `app/integrations/providers/gemini.py` (impl)
- Pattern: Abstract class; concrete providers registered via `register_provider_factory()` in `app/ai_providers/registry.py`

**SlidingWindowLimiterPort:**
- Purpose: Rate limiter abstraction (in-memory vs Redis)
- Examples: `app/core/limiters/protocol.py`, `app/core/limiters/memory_sliding_window.py`, `app/core/limiters/redis_sliding_window.py`
- Pattern: Protocol (structural subtyping); factory in `app/core/limiters/factory.py` selects implementation at startup

**Repository pattern:**
- Purpose: Owner-scoped persistence; services never query ORM directly
- Examples: `app/repositories/bot_repository.py`, `app/repositories/ai_chat_repository.py`
- Pattern: Constructor receives `AsyncSession`; all queries filter by `owner_id`

**NicheConversationFlowDefinition:**
- Purpose: Per-industry sales funnel definition (fields, scripts, qualification rules)
- Examples: `app/lib/niche_flow/education.py`, `app/lib/niche_flow/healthcare.py`, `app/lib/niche_flow/dev_agency.py`
- Pattern: Registry pattern; `get_niche_conversation_flow_or_generic()` in `app/lib/niche_flow/registry.py`

**Domain exceptions:**
- Purpose: Service-layer errors that carry HTTP status code and structured `code` field; caught by global handlers
- Examples: `app/services/auth_exceptions.py`, `app/services/billing_exceptions.py`, `app/services/ai_exceptions.py`
- Pattern: Each domain defines a base exception class; `app/core/exception_handlers.py` maps them to JSON responses

## Entry Points

**ASGI Application:**
- Location: `app/main.py` — `create_app()` builds and returns `FastAPI`; `app = create_app()` module-level
- Triggers: `uvicorn main:app` (via `main.py` wrapper) or process manager
- Responsibilities: Configures logging, registers middleware, registers exception handlers, mounts `api_router`

**Root launcher:**
- Location: `main.py` (repo root)
- Triggers: `python main.py` or `uvicorn main:app`
- Responsibilities: Reads settings, calls `uvicorn.run("app.main:app", ...)`

**Knowledge ingestion worker:**
- Location: `app/workers/knowledge_ingestion_worker.py`
- Triggers: `python -m app.workers.knowledge_ingestion_worker` (separate process)
- Responsibilities: BRPOP Redis queue, PDF processing pipeline, retry/dead-letter logic

## Architectural Constraints

- **Threading:** Single-threaded async event loop (uvicorn/asyncio); all I/O uses `async/await`. Workers use `asyncio.run()` independently.
- **Global state:** Three module-level singletons — `_engine`/`_session_maker` (`app/core/db.py`), `Settings` LRU cache (`app/core/config.py`), Redis client (`app/core/redis_client.py`). All are initialized lazily or in lifespan, disposed on shutdown.
- **Circular imports:** `app/api/deps.py` imports from nearly every service and repository; it is the DI wiring file and must not be imported by services or repositories.
- **Owner scoping:** All repository methods filter by `owner_id`. Admin endpoints use `app/repositories/*_platform_admin_repository.py` or explicit `admin_*` repository methods — never bypass owner filters on regular repos.
- **Settings isolation:** `Settings` is read-only pydantic model loaded from env; never mutated at runtime. `get_settings()` is `@lru_cache` — same object across all calls in a process.

## Anti-Patterns

### Business logic in route handlers

**What happens:** Adding DB queries or domain decisions directly inside `app/api/v1/*.py` route functions.
**Why it's wrong:** Handlers are tested only via HTTP; logic becomes untestable without full HTTP stack; bypasses the service transaction boundary.
**Do this instead:** Route handler calls a service method; service method owns the logic. See `app/api/v1/bot_chat.py` → `BotChatTestService` as the correct pattern.

### Importing services/repositories from `app/lib/`

**What happens:** `app/lib/` files importing from `app/services/` or `app/repositories/`.
**Why it's wrong:** `app/lib/` is the pure-logic layer (no DB, no service deps); pulling services in creates circular imports and breaks isolation.
**Do this instead:** `app/lib/` depends only on `app/models/` (for types) and stdlib. Pass data explicitly from the service layer.

### Direct ORM queries in service methods

**What happens:** `session.execute(select(Bot).where(...))` directly inside a service class.
**Why it's wrong:** Bypasses the owner-scoping contract and duplicates query logic that the repository already encapsulates.
**Do this instead:** Services call repository methods (e.g., `BotRepository.get_bot_by_id(owner_id=..., bot_id=...)`) and never construct SQLAlchemy queries themselves.

## Error Handling

**Strategy:** Domain exception hierarchy + centralized global handlers.

**Patterns:**
- Each service module defines a base exception class (e.g., `AuthServiceError`, `BillingError`) with `status_code` and `code` fields.
- Route handlers do not catch domain exceptions; they propagate to `app/core/exception_handlers.py`.
- All responses use `StandardErrorResponse` / `ErrorInfo` schema (`app/core/error_response.py`) for consistent JSON shape.
- 5xx errors are reported to Sentry via `capture_exception()` / `report_server_mapped_error()` (`app/core/error_tracking.py`).
- AI pipeline errors propagate as `AIServiceHTTPError` subclasses; the global handler sanitizes them before reaching public widget callers.

## Cross-Cutting Concerns

**Logging:** `structlog` with `contextvars` binding; configured in `app/core/logging.py`. JSON mode in production. `RequestLoggingMiddleware` binds `request_id`, `correlation_id`, `bot_id`, `channel` per request (`app/core/middleware.py`). Module loggers via `get_logger(__name__)`.

**Validation:** Pydantic v2 schemas in `app/schemas/` for all API request/response bodies. ORM models use SQLAlchemy `CheckConstraint` for DB-level invariants.

**Authentication:** JWT (HS256, 15 min access / 7 day refresh) or optional HttpOnly cookie mode. Bearer token resolved in `app/api/auth_http.py`; cookie resolved in `app/core/auth_cookies.py`. CSRF protection when cookie mode is active (`app/api/auth_csrf.py`). RBAC via `app/core/rbac.py` (two roles: `customer_admin`, `superadmin`).

---

*Architecture analysis: 2026-05-30*
