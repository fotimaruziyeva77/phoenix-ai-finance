"""
Map configured provider ids to concrete :class:`~app.ai_providers.base.AIProvider` instances.

Implementations are registered here from ``app.integrations.providers`` (Gemini today); add
``register_provider_factory`` for new vendors without changing :class:`~app.services.ai_service.AIService`.
"""

from __future__ import annotations

from collections.abc import Callable

from app.ai_providers.base import AIProvider
from app.ai_providers.exceptions import MissingAIProviderCredentialsError, UnknownAIProviderError
from app.core.config import Settings
from app.integrations.providers.gemini import GeminiProvider
from app.integrations.providers.ollama import OllamaProvider

ProviderFactory = Callable[[Settings], AIProvider]

_DEFAULT_PROVIDER_ID = "gemini"

_FACTORIES: dict[str, ProviderFactory] = {}


def register_provider_factory(provider_id: str, factory: ProviderFactory) -> None:
    """Register or replace a provider implementation (tests or plugins)."""
    _FACTORIES[provider_id.strip().lower()] = factory


def _build_gemini(settings: Settings) -> AIProvider:
    key = settings.gemini_api_key
    if not key or not str(key).strip():
        raise MissingAIProviderCredentialsError("gemini", "Set GEMINI_API_KEY or APP_GEMINI_API_KEY")
    return GeminiProvider.from_settings(settings)


register_provider_factory("gemini", _build_gemini)


def _build_ollama(settings: Settings) -> AIProvider:
    return OllamaProvider.from_settings(settings)


register_provider_factory("ollama", _build_ollama)


def resolve_ai_provider(settings: Settings, provider_id: str | None = None) -> AIProvider:
    """
    Resolve ``provider_id`` (e.g. from future bot config) to a live provider.

    ``None``, empty string, or whitespace-only selects the default (``gemini`` today).
    """
    if provider_id is None:
        key = _DEFAULT_PROVIDER_ID
    else:
        stripped = provider_id.strip()
        key = _DEFAULT_PROVIDER_ID if not stripped else stripped.lower()
    factory = _FACTORIES.get(key)
    if factory is None:
        raise UnknownAIProviderError(key)
    return factory(settings)


def default_provider_id() -> str:
    return _DEFAULT_PROVIDER_ID


def registered_provider_ids() -> frozenset[str]:
    return frozenset(_FACTORIES.keys())
