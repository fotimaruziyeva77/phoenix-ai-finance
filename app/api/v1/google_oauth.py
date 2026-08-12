"""Google OAuth 2.0 authorization code flow (browser redirects + token exchange)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.api.deps import (
    GoogleOAuthServiceDep,
    SettingsDep,
    rate_limit_oauth_google_callback,
    rate_limit_oauth_google_start,
)
from app.api.auth_openapi import OAUTH_CALLBACK_OPENAPI_RESPONSES
from app.core.request_client import client_ip

router = APIRouter(tags=["auth"])


@router.get(
    "/google/start",
    summary="Start Google sign-in",
    response_class=RedirectResponse,
)
async def google_oauth_start(
    request: Request,
    _: Annotated[None, Depends(rate_limit_oauth_google_start)],
    google_oauth: GoogleOAuthServiceDep,
) -> RedirectResponse:
    return RedirectResponse(url=google_oauth.build_authorize_url(), status_code=302)


@router.get(
    "/google/callback",
    summary="Google OAuth callback (registered redirect_uri)",
    response_class=RedirectResponse,
    responses=OAUTH_CALLBACK_OPENAPI_RESPONSES,
)
async def google_oauth_callback(
    request: Request,
    _: Annotated[None, Depends(rate_limit_oauth_google_callback)],
    google_oauth: GoogleOAuthServiceDep,
    settings: SettingsDep,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
) -> RedirectResponse:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    ua = request.headers.get("user-agent")
    location = await google_oauth.complete_callback_redirect_url(
        code=code,
        state=state,
        provider_error=error,
        client_ip=ip,
        user_agent=ua,
    )
    return RedirectResponse(url=location, status_code=302)
