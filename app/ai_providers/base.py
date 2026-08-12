"""Abstract AI provider contract (not tied to any vendor SDK)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage


class AIProvider(ABC):
    """
    Vendor-neutral completion API.

    Callers use :meth:`generate_response` for inference. :meth:`parse_usage` and
    :meth:`normalize_error` support persistence and consistent error surfaces
    without importing provider SDKs elsewhere.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable registry key, e.g. ``gemini``."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Model id used when bot config leaves ``model_name`` blank."""

    @abstractmethod
    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        """Perform one model call; return :class:`NormalizedAIResult` (do not raise for expected API errors)."""

    @abstractmethod
    def parse_usage(self, raw: Mapping[str, Any] | None) -> TokenUsage | None:
        """Map provider usage payload (e.g. JSON dict) to :class:`TokenUsage`; return None if unknown."""

    @abstractmethod
    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        """Return ``(error_code, message)`` for logging and API mapping."""
