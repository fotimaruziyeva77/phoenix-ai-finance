"""Unit tests for AI error classification (no HTTP)."""

from __future__ import annotations

import uuid

from app.schemas.ai_chat import SendBotMessageResult
from app.services.ai_error_taxonomy import (
    AI_CATEGORY_AUTH_CONFIG,
    AI_CATEGORY_INVALID_PROVIDER_RESPONSE,
    AI_CATEGORY_PROVIDER_UNAVAILABLE,
    AI_CATEGORY_TIMEOUT,
    api_error_code_for_category,
    classify_provider_error_code,
    exception_for_failed_send_result,
    http_status_for_category,
    is_retryable_category,
)


def test_classify_timeout() -> None:
    assert classify_provider_error_code("timeout") == AI_CATEGORY_TIMEOUT


def test_classify_auth() -> None:
    assert classify_provider_error_code("auth_failed") == AI_CATEGORY_AUTH_CONFIG


def test_classify_rate_and_connection() -> None:
    assert classify_provider_error_code("rate_limited") == AI_CATEGORY_PROVIDER_UNAVAILABLE
    assert classify_provider_error_code("connection_error") == AI_CATEGORY_PROVIDER_UNAVAILABLE


def test_classify_invalid_response_family() -> None:
    assert classify_provider_error_code("invalid_response") == AI_CATEGORY_INVALID_PROVIDER_RESPONSE
    assert classify_provider_error_code("empty_completion") == AI_CATEGORY_INVALID_PROVIDER_RESPONSE
    assert classify_provider_error_code("http_400") == AI_CATEGORY_INVALID_PROVIDER_RESPONSE


def test_api_code_rate_limit_overrides_category() -> None:
    cat = AI_CATEGORY_PROVIDER_UNAVAILABLE
    assert (
        api_error_code_for_category(cat, provider_error_code="rate_limited") == "ai_rate_limited"
    )


def test_http_status_timeout_is_504() -> None:
    from starlette import status

    assert http_status_for_category(AI_CATEGORY_TIMEOUT) == status.HTTP_504_GATEWAY_TIMEOUT


def test_retryable_flags() -> None:
    assert is_retryable_category(AI_CATEGORY_TIMEOUT) is True
    assert is_retryable_category(AI_CATEGORY_AUTH_CONFIG) is False
    assert (
        is_retryable_category(
            AI_CATEGORY_PROVIDER_UNAVAILABLE,
            provider_error_code="rate_limited",
        )
        is True
    )


def test_exception_for_failed_send_timeout_http_and_codes() -> None:
    exc = exception_for_failed_send_result(
        SendBotMessageResult(
            conversation_id=uuid.uuid4(),
            user_message_id=uuid.uuid4(),
            success=False,
            error_code="timeout",
        ),
    )
    assert exc.client_status_code == 504
    assert exc.client_code == "ai_timeout"
    assert exc.ai_category == AI_CATEGORY_TIMEOUT
    assert exc.details is not None
    assert exc.details.get("retryable") is True


def test_exception_for_failed_send_auth_config() -> None:
    exc = exception_for_failed_send_result(
        SendBotMessageResult(
            conversation_id=uuid.uuid4(),
            user_message_id=uuid.uuid4(),
            success=False,
            error_code="auth_failed",
        ),
    )
    assert exc.client_code == "ai_auth_config"
    assert exc.ai_category == AI_CATEGORY_AUTH_CONFIG
    assert exc.details is not None
    assert exc.details.get("retryable") is False


def test_exception_for_failed_send_invalid_response() -> None:
    exc = exception_for_failed_send_result(
        SendBotMessageResult(
            conversation_id=uuid.uuid4(),
            user_message_id=uuid.uuid4(),
            success=False,
            error_code="invalid_response",
        ),
    )
    assert exc.client_code == "ai_invalid_provider_response"
    assert exc.ai_category == AI_CATEGORY_INVALID_PROVIDER_RESPONSE
