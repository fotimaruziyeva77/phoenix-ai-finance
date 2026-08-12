"""
AI inference: vendor-neutral :class:`~app.ai_providers.base.AIProvider` contract and registry.

Concrete integrations (HTTP, SDKs) live under ``app.integrations.providers`` and are wired in
:mod:`app.ai_providers.registry` — keeps orchestration and prompts free of vendor imports.
"""

from app.ai_providers.base import AIProvider
from app.ai_providers.exceptions import MissingAIProviderCredentialsError, UnknownAIProviderError
from app.ai_providers.gemini import GeminiProvider
from app.ai_providers.registry import (
    default_provider_id,
    register_provider_factory,
    registered_provider_ids,
    resolve_ai_provider,
)
from app.ai_providers.types import ChatMessage, GenerateParams, NormalizedAIResult, TokenUsage

__all__ = [
    "AIProvider",
    "ChatMessage",
    "GeminiProvider",
    "GenerateParams",
    "MissingAIProviderCredentialsError",
    "NormalizedAIResult",
    "TokenUsage",
    "UnknownAIProviderError",
    "default_provider_id",
    "register_provider_factory",
    "registered_provider_ids",
    "resolve_ai_provider",
]
