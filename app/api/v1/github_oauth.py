"""GitHub OAuth 2.0 authorization code flow (browser redirects + shared token exchange)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse

from app.api.deps import (
    GithubOAuthServiceDep,
    SettingsDep,
    rate_limit_oauth_github_callback,
    rate_limit_oauth_github_start,
)
from app.api.auth_openapi import OAUTH_CALLBACK_OPENAPI_RESPONSES
from app.core.request_client import client_ip

router = APIRouter(tags=["auth"])


@router.get(
    "/github/start",
    summary="Start GitHub sign-in",
    response_class=RedirectResponse,
)
async def github_oauth_start(
    request: Request,
    _: Annotated[None, Depends(rate_limit_oauth_github_start)],
    github_oauth: GithubOAuthServiceDep,
) -> RedirectResponse:
    return RedirectResponse(url=github_oauth.build_authorize_url(), status_code=302)


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback (registered Authorization callback URL)",
    response_class=RedirectResponse,
    responses=OAUTH_CALLBACK_OPENAPI_RESPONSES,
)
async def github_oauth_callback(
    request: Request,
    _: Annotated[None, Depends(rate_limit_oauth_github_callback)],
    github_oauth: GithubOAuthServiceDep,
    settings: SettingsDep,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> RedirectResponse:
    _ = error_description  # GitHub may send it; we only branch on ``error``.
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    ua = request.headers.get("user-agent")
    location = await github_oauth.complete_callback_redirect_url(
        code=code,
        state=state,
        provider_error=error,
        client_ip=ip,
        user_agent=ua,
    )
    return RedirectResponse(url=location, status_code=302)
