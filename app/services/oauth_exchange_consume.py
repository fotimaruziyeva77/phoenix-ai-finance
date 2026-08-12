"""Turn one-time browser OAuth exchange codes into ``AuthSessionResponse``."""

from __future__ import annotations

from pydantic import ValidationError

from app.integrations.oauth_exchange_store import OAuthExchangeStore
from app.schemas.auth import AuthSessionResponse
from app.services.auth_exceptions import OAuthExchangeInvalidError


def consume_oauth_exchange_code(store: OAuthExchangeStore, exchange_code: str) -> AuthSessionResponse:
    raw = store.pop(exchange_code)
    if raw is None:
        raise OAuthExchangeInvalidError()
    try:
        return AuthSessionResponse.model_validate_json(raw)
    except (ValueError, ValidationError) as e:
        raise OAuthExchangeInvalidError("Invalid OAuth exchange payload") from e
