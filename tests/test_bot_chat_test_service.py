"""Unit tests for dashboard chat service error mapping."""

from __future__ import annotations

import uuid

import pytest
from app.schemas.ai_chat import SendBotMessageResult
from app.services.ai_error_taxonomy import (
    AI_CATEGORY_INTERNAL_UNKNOWN,
    AI_CATEGORY_PROVIDER_UNAVAILABLE,
    AI_CATEGORY_TIMEOUT,
    API_CODE_PERSISTENCE,
    API_CODE_RATE_LIMITED,
    API_CODE_TIMEOUT,
    exception_for_failed_send_result,
)
from app.services.ai_exceptions import (
    AIServiceInferenceFailedError,
    AIServicePersistenceError,
    AIServiceRateLimitedError,
)


def _failed_result(
    *,
    error_code: str | None,
    error_message: str | None = "msg",
    error_category: str | None = None,
) -> SendBotMessageResult:
    return SendBotMessageResult(
        conversation_id=uuid.uuid4(),
        user_message_id=uuid.uuid4(),
        assistant_message_id=None,
        assistant_text=None,
        model_name=None,
        success=False,
        error_code=error_code,
        error_message=error_message,
        error_category=error_category,
        latency_ms=1,
        tokens_input=0,
        tokens_output=0,
        tokens_total=0,
        cost_usd=None,
    )


def test_exception_maps_persistence_to_500_with_category() -> None:
    with pytest.raises(AIServicePersistenceError) as ei:
        raise exception_for_failed_send_result(_failed_result(error_code="persistence_error"))
    assert ei.value.client_status_code == 500
    assert ei.value.client_code == API_CODE_PERSISTENCE
    assert ei.value.ai_category == AI_CATEGORY_INTERNAL_UNKNOWN
    assert ei.value.details and ei.value.details.get("retryable") is False


def test_exception_maps_rate_limit_to_429() -> None:
    with pytest.raises(AIServiceRateLimitedError) as ei:
        raise exception_for_failed_send_result(_failed_result(error_code="rate_limited"))
    assert ei.value.client_status_code == 429
    assert ei.value.client_code == API_CODE_RATE_LIMITED
    assert ei.value.ai_category == AI_CATEGORY_PROVIDER_UNAVAILABLE
    assert ei.value.details and ei.value.details.get("retryable") is True


def test_exception_maps_timeout_to_504_and_code() -> None:
    with pytest.raises(AIServiceInferenceFailedError) as ei:
        raise exception_for_failed_send_result(_failed_result(error_code="timeout"))
    assert ei.value.client_status_code == 504
    assert ei.value.client_code == API_CODE_TIMEOUT
    assert ei.value.ai_category == AI_CATEGORY_TIMEOUT
