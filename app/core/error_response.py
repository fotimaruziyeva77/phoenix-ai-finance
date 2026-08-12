from typing import Any

from pydantic import BaseModel, Field


class ErrorInfo(BaseModel):
    """Public error payload (safe for clients; never includes stack traces)."""

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    request_id: str | None = None
    category: str | None = Field(
        default=None,
        description="Optional grouping (e.g. authentication) for clients and observability.",
    )
    ai_category: str | None = Field(
        default=None,
        description="When category is ai_chat: normalized failure class (timeout, auth_config, …).",
    )
    details: Any | None = None


class StandardErrorResponse(BaseModel):
    error: ErrorInfo
