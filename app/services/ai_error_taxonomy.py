"""
Normalized AI failure taxonomy for clients, logs, and HTTP mapping.

Maps provider-local ``error_code`` strings (e.g. from :mod:`app.integrations.providers.gemini_errors`)
into a small set of stable categories. User-visible messages stay generic unless the provider
already supplied a redacted, safe string via orchestration.
"""

from __future__ import annotations

from typing import Final

from app.schemas.ai_chat import SendBotMessageResult
from app.services.ai_exceptions import (
    AIServiceHTTPError,
    AIServiceInferenceFailedError,
    AIServicePersistenceError,
    AIServiceRateLimitedError,
)

# --- Stable categories (JSON field ``ai_category``) — use for UI/analytics, not provider enums ---
AI_CATEGORY_TIMEOUT: Final = "timeout"
AI_CATEGORY_AUTH_CONFIG: Final = "auth_config"
AI_CATEGORY_PROVIDER_UNAVAILABLE: Final = "provider_unavailable"
AI_CATEGORY_INVALID_PROVIDER_RESPONSE: Final = "invalid_provider_response"
AI_CATEGORY_INTERNAL_UNKNOWN: Final = "internal_unknown"

# --- Stable API error ``code`` values (subset; persistence keeps its own code) ---
API_CODE_TIMEOUT: Final = "ai_timeout"
API_CODE_AUTH_CONFIG: Final = "ai_auth_config"
API_CODE_PROVIDER_UNAVAILABLE: Final = "ai_provider_unavailable"
API_CODE_INVALID_PROVIDER_RESPONSE: Final = "ai_invalid_provider_response"
API_CODE_INTERNAL_UNKNOWN: Final = "ai_internal_unknown"
API_CODE_RATE_LIMITED: Final = "ai_rate_limited"
API_CODE_PERSISTENCE: Final = "ai_persistence_error"

_DEFAULT_MESSAGES: dict[str, str] = {
    AI_CATEGORY_TIMEOUT: "The AI service took too long to respond. Try again in a moment.",
    AI_CATEGORY_AUTH_CONFIG: "AI credentials or configuration are invalid. Check your workspace setup.",
    AI_CATEGORY_PROVIDER_UNAVAILABLE: "The AI service is temporarily unavailable. Try again shortly.",
    AI_CATEGORY_INVALID_PROVIDER_RESPONSE: "The AI service returned an unexpected response. Try again or adjust your bot settings.",
    AI_CATEGORY_INTERNAL_UNKNOWN: "Something went wrong while processing your request. Try again later.",
}


def classify_provider_error_code(provider_error_code: str | None) -> str:
    """Map provider / transport error_code into :mod:`AI_CATEGORY_*` constants."""
    c = (provider_error_code or "").strip().lower()
    if c in ("embedding_failed",):
        return AI_CATEGORY_PROVIDER_UNAVAILABLE
    if c in ("timeout",):
        return AI_CATEGORY_TIMEOUT
    if c in ("auth_failed",):
        return AI_CATEGORY_AUTH_CONFIG
    if c in (
        "rate_limited",
        "provider_error",
        "connection_error",
        "request_error",
    ):
        return AI_CATEGORY_PROVIDER_UNAVAILABLE
    if c in ("invalid_response", "invalid_request", "empty_completion") or (
        c.startswith("http_") and not c.startswith("http_401") and not c.startswith("http_403")
    ):
        return AI_CATEGORY_INVALID_PROVIDER_RESPONSE
    if c in ("persistence_error", "unexpected_error", "unknown", ""):
        return AI_CATEGORY_INTERNAL_UNKNOWN
    return AI_CATEGORY_INTERNAL_UNKNOWN


def api_error_code_for_category(category: str, *, provider_error_code: str | None = None) -> str:
    """Public ``error.code`` for JSON (distinct from HTTP status)."""
    if (provider_error_code or "").strip().lower() == "rate_limited":
        return API_CODE_RATE_LIMITED
    return {
        AI_CATEGORY_TIMEOUT: API_CODE_TIMEOUT,
        AI_CATEGORY_AUTH_CONFIG: API_CODE_AUTH_CONFIG,
        AI_CATEGORY_PROVIDER_UNAVAILABLE: API_CODE_PROVIDER_UNAVAILABLE,
        AI_CATEGORY_INVALID_PROVIDER_RESPONSE: API_CODE_INVALID_PROVIDER_RESPONSE,
        AI_CATEGORY_INTERNAL_UNKNOWN: API_CODE_INTERNAL_UNKNOWN,
    }.get(category, API_CODE_INTERNAL_UNKNOWN)


def http_status_for_category(category: str, *, provider_error_code: str | None = None) -> int:
    from starlette import status

    if (provider_error_code or "").strip().lower() == "rate_limited":
        return status.HTTP_429_TOO_MANY_REQUESTS
    if category == AI_CATEGORY_TIMEOUT:
        return status.HTTP_504_GATEWAY_TIMEOUT
    if category == AI_CATEGORY_AUTH_CONFIG:
        return status.HTTP_502_BAD_GATEWAY
    if category == AI_CATEGORY_PROVIDER_UNAVAILABLE:
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if category == AI_CATEGORY_INVALID_PROVIDER_RESPONSE:
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_502_BAD_GATEWAY


def is_retryable_category(category: str, *, provider_error_code: str | None = None) -> bool:
    if (provider_error_code or "").strip().lower() == "rate_limited":
        return True
    return category in (
        AI_CATEGORY_TIMEOUT,
        AI_CATEGORY_PROVIDER_UNAVAILABLE,
    )


def user_safe_message(*, category: str, provider_message: str | None) -> str:
    """Prefer orchestration-safe provider text; fall back to category default."""
    pm = (provider_message or "").strip()
    if pm:
        return pm
    return _DEFAULT_MESSAGES.get(category, _DEFAULT_MESSAGES[AI_CATEGORY_INTERNAL_UNKNOWN])


PERSISTENCE_USER_MESSAGE = (
    "Your message was saved, but we could not finish saving the AI reply. "
    "You can send another message or refresh the thread."
)


def exception_for_failed_send_result(result: SendBotMessageResult) -> AIServiceHTTPError:
    """
    Build the HTTP-layer exception for a failed :class:`~app.schemas.ai_chat.SendBotMessageResult`.

    No synthetic assistant success: the client receives a structured error; the user turn may
    already exist in the database (committed before the provider call).
    """
    code = (result.error_code or "unknown").strip().lower()
    base_details: dict[str, object] = {"provider_error_code": result.error_code or "unknown"}

    if code == "persistence_error":
        msg = (result.error_message or "").strip() or PERSISTENCE_USER_MESSAGE
        return AIServicePersistenceError(
            msg,
            details={
                **base_details,
                "ai_category": AI_CATEGORY_INTERNAL_UNKNOWN,
                "retryable": False,
            },
            ai_category=AI_CATEGORY_INTERNAL_UNKNOWN,
            client_status_code=500,
            client_code=API_CODE_PERSISTENCE,
        )

    if code == "rate_limited":
        cat = AI_CATEGORY_PROVIDER_UNAVAILABLE
        msg = user_safe_message(category=cat, provider_message=result.error_message)
        return AIServiceRateLimitedError(
            msg,
            details={
                **base_details,
                "ai_category": cat,
                "retryable": True,
            },
            ai_category=cat,
        )

    category = result.error_category or classify_provider_error_code(result.error_code)
    msg = user_safe_message(category=category, provider_message=result.error_message)
    st = http_status_for_category(category, provider_error_code=result.error_code)
    pub = api_error_code_for_category(category, provider_error_code=result.error_code)
    retry = is_retryable_category(category, provider_error_code=result.error_code)

    return AIServiceInferenceFailedError(
        msg,
        details={**base_details, "ai_category": category, "retryable": retry},
        ai_category=category,
        client_status_code=st,
        client_code=pub,
    )
