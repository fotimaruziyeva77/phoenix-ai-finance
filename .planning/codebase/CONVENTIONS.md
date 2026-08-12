# Coding Conventions

**Analysis Date:** 2026-05-30

## Naming Patterns

**Files:**
- `snake_case.py` throughout — e.g. `billing_service.py`, `lead_scoring.py`, `gemini_text_embedding.py`
- Test files prefixed with `test_` — e.g. `test_lead_scoring.py`, `test_gemini_provider.py`
- Unit-only tests end with `_unit.py` — e.g. `test_rbac_authz_unit.py`, `test_vector_cosine_unit.py`
- Integration tests end with `_integration.py` — e.g. `test_leads_api_integration.py`

**Functions:**
- `snake_case` for all functions: `score_lead()`, `get_plan_limits()`, `create_checkout_session()`
- Private/internal helpers prefixed with single underscore: `_norm_intent()`, `_ts_to_dt()`, `_safe_user_id()`, `_config_for_niche()`
- Private methods on classes use single underscore: `self._sub`, `self._users`, `self._stripe_module()`
- Module-level constants: `SCREAMING_SNAKE_CASE` — `DEFAULT_LEAD_SCORING_CONFIG`, `NICHE_SCORING_CONFIG`
- Module-level private loggers: `_LOG = get_logger(__name__)` (39 files follow this pattern)

**Variables:**
- `snake_case` for locals and instance vars
- Type aliases use `PascalCase`: `LeadTemperature = Literal["cold", "warm", "hot"]`
- Keyword-only arguments used extensively for public API functions: `score_lead(*, niche_id, detected_intent, ...)`

**Types:**
- `PascalCase` for classes, dataclasses, exceptions, Pydantic models, and type aliases
- Exception hierarchies use class variables for HTTP codes and stable string codes:
  ```python
  class BillingError(Exception):
      status_code: ClassVar[int] = 400
      code: ClassVar[str] = "billing_error"
      default_message: ClassVar[str] = "Billing operation failed"
  ```
- Enums use `PascalCase` class names with `snake_case` values: `ConversationFlowState.start`, `PlanSlug.free`

## Code Style

**Formatting:**
- Tool: `ruff format`
- Quote style: double quotes
- Indent style: spaces (4-space, standard Python)
- Line length: 120 chars (`ruff` target), `E501` (line-too-long) explicitly ignored in `pyproject.toml`

**Linting:**
- Tool: `ruff` with rules `E4`, `E7`, `E9`, `F`, `I` (pyflakes + isort)
- `F821` (undefined names in forward references) suppressed for `app/models/**/*.py` — SQLAlchemy `Mapped["Model"]` forward refs
- Config: `pyproject.toml`

## Import Organization

**Order enforced by ruff `I` (isort):**
1. `from __future__ import annotations` — present in virtually every app module (250+ files)
2. Standard library imports
3. Third-party imports (`fastapi`, `pydantic`, `sqlalchemy`, `httpx`, etc.)
4. Local application imports (`from app.core…`, `from app.services…`, etc.)

**Path Aliases:**
- No path aliases configured — all imports use absolute `app.*` paths
- `pythonpath = .` in `pytest.ini` makes `app` importable directly in tests

**TYPE_CHECKING guard:**
- Used to break circular imports for type annotations:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from app.models.user import User
  ```

## Error Handling

**Exception Hierarchy Pattern:**
- Domain-specific base errors extend `Exception` with class-level `status_code`, `code`, and `default_message` attributes: `app/services/billing_exceptions.py`, `app/services/auth_exceptions.py`, `app/services/bot_exceptions.py`
- Narrower errors subclass the domain base: `BotLimitExceededError(PlanLimitExceededError)` subclasses `PlanLimitExceededError(BillingError)`
- AI provider errors are **not raised to callers** — `generate_response()` returns `NormalizedAIResult` with `success=False` and `error_code`/`error_message` populated: `app/ai_providers/base.py`
- HTTP exception mapping via FastAPI `exception_handlers`: `app/core/exception_handlers.py`
- Error responses always use the `StandardErrorResponse` envelope: `app/core/error_response.py`
  ```python
  class StandardErrorResponse(BaseModel):
      error: ErrorInfo  # code, message, request_id, category (no stack traces)
  ```

**Raise Pattern:**
- Raise domain exceptions at the service boundary, convert to HTTP in handlers
- Never expose stack traces in API responses (enforced via `ErrorInfo` model)
- Lazy-import optional dependencies: raise `StripeNotConfiguredError` if `stripe` package missing

## Logging

**Framework:** `structlog` with `get_logger()` factory in `app/core/logging.py`

**Patterns:**
- Module-level private logger: `_LOG = get_logger(__name__)`
- Structured key-value logging (never f-strings in log calls):
  ```python
  _LOG.info("subscription_provisioned_free", user_id=str(user.id))
  _LOG.warning("bot_limit_exceeded", user_id=str(user.id), plan=limits.slug, current=..., max_allowed=...)
  _LOG.error("stripe_webhook_handler_error", event_type=event_type, event_id=event_id, error=str(exc))
  ```
- Event name is the first positional argument (snake_case verb-noun): `"stripe_checkout_created"`, `"auth_audit"`, `"application_startup"`
- Auth events log to a dedicated `auth_audit` logger: `app/core/auth_audit.py`
- **Security rule**: Never log passwords, tokens, refresh tokens, OAuth codes (documented in `app/core/auth_audit.py` docstring)
- JSON or console output configurable via `settings.log_json`

## Comments

**When to Comment:**
- Module-level docstrings on every file explaining what the module owns: `"""Billing service — subscription management, plan enforcement, Stripe integration."""`
- Class docstrings for public abstractions and config dataclasses
- Section dividers with `# ---` or `# --` comment blocks to group methods in large services
- Inline `# Future:` and `# TODO` comments for deferred decisions
- Checklist-style docstrings in tests: `"""Checklist (3): access JWT round-trip and required claims."""`

**Module Documentation:**
- Substantial multi-paragraph module docstrings common in complex service files (e.g. `app/services/lead_scoring.py` — full scoring algorithm spec in module docstring)

## Function Design

**Size:** Functions are kept focused; large services decompose into private helper methods (`_on_checkout_completed`, `_on_subscription_updated`, etc.)

**Parameters:**
- Public API functions with >2 meaningful inputs use keyword-only arguments (`*` separator): `score_lead(*, niche_id, detected_intent, collected_data_json, ...)`
- Dependency injection via constructor: services accept repositories and settings as `__init__` arguments
- Optional dependencies typed as `X | None = None`: `redis_client: Any | None = None`

**Return Values:**
- Typed return annotations on all functions
- Frozen dataclasses for multi-field results: `LeadScoreResult`, `NormalizedAIResult`
- `None` returns for void async operations; explicit `str` for URL returns

## Module Design

**Exports:**
- `__all__` used selectively on modules with a deliberate public surface (59 files)
- Re-export pattern used for provider isolation: `app/ai_providers/gemini.py` re-exports `GeminiProvider` from `app/integrations/providers/gemini.py`

**Barrel Files:**
- `__init__.py` files used as selective re-export points in `app/core/security/`, `app/ai_providers/`, `app/lib/niche_flow/`, `app/prompting/`
- Empty `__init__.py` in most package dirs (not used as barrels)

## Data Shapes

**Pydantic Schemas:**
- ORM-readable schemas use `model_config = ConfigDict(from_attributes=True)`
- Field constraints inline with `Field(..., ge=0)`, `Field(..., min_length=1)`
- `from __future__ import annotations` used with forward references in schemas

**Dataclasses:**
- Immutable value objects use `@dataclass(frozen=True, slots=True)`: `ChatMessage`, `GenerateParams`, `NormalizedAIResult`, `LeadScoreResult`
- Config objects also use frozen dataclasses: `LeadScoringConfig`

**SQLAlchemy Models:**
- All inherit from `app/models/base.py` `Base(DeclarativeBase)`
- Async session via `AsyncSession` from `sqlalchemy.ext.asyncio`

---

*Convention analysis: 2026-05-30*
