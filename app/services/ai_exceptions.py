"""AI orchestration errors (HTTP layer maps :class:`AIServiceHTTPError` subclasses)."""

from __future__ import annotations

from typing import Any, ClassVar


class AIServiceError(Exception):
    """Base for AI service failures."""


class AIServiceHTTPError(AIServiceError):
    """
    Structured error for API responses (stable ``code`` + optional ``details``).

    ``client_status_code`` / ``client_code`` override class defaults when inference failures
    need distinct HTTP status or public error codes (see :mod:`app.services.ai_error_taxonomy`).
    """

    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "ai_error"
    default_message: ClassVar[str] = "AI request failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        ai_category: str | None = None,
        client_status_code: int | None = None,
        client_code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        self.ai_category = ai_category
        self._client_status_code = client_status_code if client_status_code is not None else type(self).status_code
        self._client_code = client_code if client_code is not None else type(self).code
        super().__init__(self.message)

    @property
    def client_status_code(self) -> int:
        return self._client_status_code

    @property
    def client_code(self) -> str:
        return self._client_code


class AIServiceForbiddenError(AIServiceHTTPError):
    """Bot or conversation is not accessible to the authenticated user."""

    status_code = 403
    code = "ai_forbidden"
    default_message = "You do not have access to this bot"


class AIServiceBotPlatformSuspendedError(AIServiceHTTPError):
    """Bot is suspended by platform operators (dashboard test chat blocked)."""

    status_code = 403
    code = "ai_bot_platform_suspended"
    default_message = "This bot has been suspended by the platform."


class AIServiceNotFoundError(AIServiceHTTPError):
    """Conversation or related entity not found for this bot/user."""

    status_code = 404
    code = "ai_not_found"
    default_message = "Resource was not found"


class AIServiceValidationError(AIServiceHTTPError):
    """Invalid input (empty message, archived bot, etc.)."""

    status_code = 422
    code = "ai_validation_error"
    default_message = "Invalid AI chat request"


class AIServiceInferenceFailedError(AIServiceHTTPError):
    """Provider returned no completion (mapped from orchestration result, not a fake success)."""

    status_code = 502
    code = "ai_inference_failed"
    default_message = "The AI provider did not return a completion"


class AIServiceRateLimitedError(AIServiceHTTPError):
    """Upstream or quota rate limit."""

    status_code = 429
    code = "ai_rate_limited"
    default_message = "AI service rate limited; try again shortly"


class AIServiceQuotaExceededError(AIServiceHTTPError):
    """
    Token quota exhausted for ``bot_daily`` or ``owner_monthly`` (``ai_usage_logs.tokens_total``).

    ``details`` (when set) may include: ``quota_scope``, ``used_tokens``, ``cap_tokens``,
    ``measure`` (``tokens_total``), ``resets_at_utc``, ``retry_suggestion``.

    Public widget responses are sanitized in :mod:`app.core.exception_handlers` (details omitted).
    """

    status_code = 429
    code = "ai_quota_exceeded"
    default_message = "This assistant has reached a temporary usage limit. Try again later."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        ai_category: str | None = None,
        client_status_code: int | None = None,
        client_code: str | None = None,
    ) -> None:
        super().__init__(
            message,
            details=details,
            ai_category=ai_category or "quota_exceeded",
            client_status_code=client_status_code,
            client_code=client_code,
        )


class AIServicePersistenceError(AIServiceHTTPError):
    """Failed to persist chat or usage after the provider call."""

    status_code = 500
    code = "ai_persistence_error"
    default_message = "Could not save chat messages"
