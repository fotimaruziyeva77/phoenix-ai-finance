"""Provider-agnostic request/response shapes (internal contract)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ChatRole = Literal["user", "assistant", "system"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class GenerateParams:
    """Minimal, explicit inputs for a single completion call."""

    model: str
    messages: tuple[ChatMessage, ...]
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Normalized token accounting; any field may be unknown per provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedAIResult:
    """
    Single normalized outcome for logging, persistence, and UI.

    On failure: ``success`` is False, ``text`` and model/tokens may be None;
    ``raw_usage`` may still hold provider-reported usage from a partial response.
    """

    success: bool
    provider_name: str
    text: str | None
    model_name: str | None
    tokens: TokenUsage | None = None
    raw_usage: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
