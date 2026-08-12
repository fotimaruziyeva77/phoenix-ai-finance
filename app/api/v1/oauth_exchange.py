"""Exchange one-time OAuth redirect codes for API tokens (all browser OAuth providers)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.auth_http import json_auth_session_response
from app.api.deps import SettingsDep, get_oauth_exchange_store, rate_limit_oauth_exchange
from app.core.auth_audit import log_auth_event
from app.core.request_client import client_ip
from app.integrations.oauth_exchange_store import OAuthExchangeStore
from app.api.auth_openapi import OAUTH_EXCHANGE_OPENAPI_RESPONSES
from app.schemas.auth import AuthSessionResponse, OAuthExchangeRequest
from app.services.auth_exceptions import OAuthExchangeInvalidError
from app.services.oauth_exchange_consume import consume_oauth_exchange_code

router = APIRouter(tags=["auth"])


@router.post(
    "/oauth/exchange",
    summary="Exchange one-time OAuth code for JWT session",
    response_model=AuthSessionResponse,
    responses=OAUTH_EXCHANGE_OPENAPI_RESPONSES,
)
async def oauth_exchange(
    request: Request,
    _: Annotated[None, Depends(rate_limit_oauth_exchange)],
    body: OAuthExchangeRequest,
    store: Annotated[OAuthExchangeStore, Depends(get_oauth_exchange_store)],
    settings: SettingsDep,
) -> JSONResponse:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    try:
        out = consume_oauth_exchange_code(store, body.exchange_code)
        log_auth_event(
            "auth.oauth_exchange",
            outcome="success",
            client_ip=ip,
            user_id=out.user.id,
            role=out.user.role.value,
        )
        return json_auth_session_response(settings, out)
    except OAuthExchangeInvalidError as e:
        log_auth_event(
            "auth.oauth_exchange",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
        )
        raise
