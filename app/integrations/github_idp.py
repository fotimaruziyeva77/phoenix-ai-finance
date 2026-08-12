"""GitHub OAuth (authorization code) + user / email API."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.auth_exceptions import GithubOAuthProviderError

_LOG = get_logger(__name__)


def _github_error_snippet(exc: httpx.HTTPStatusError) -> str:
    """Short summary from GitHub JSON or body (no secrets)."""
    try:
        body = exc.response.json()
        if isinstance(body, dict):
            msg = body.get("message")
            err = body.get("error")
            if isinstance(msg, str) and msg.strip():
                return str(msg).strip()[:280]
            if isinstance(err, str) and err.strip():
                return str(err).strip()[:200]
            if err is not None:
                return str(err)[:200]
    except Exception:
        pass
    text = (exc.response.text or "").strip()
    return text[:200] if text else ""

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_USER = "https://api.github.com/user"
GITHUB_API_USER_EMAILS = "https://api.github.com/user/emails"


async def exchange_authorization_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    form = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data=form,
                headers={
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        snippet = _github_error_snippet(e)
        _LOG.warning(
            "github_token_exchange_http_error",
            status_code=e.response.status_code,
            detail=snippet,
        )
        msg = f"Token exchange failed ({snippet})" if snippet else "Token exchange failed"
        raise GithubOAuthProviderError(msg) from e
    except httpx.RequestError as e:
        raise GithubOAuthProviderError("Token exchange request failed") from e

    if not isinstance(data, dict):
        raise GithubOAuthProviderError("Invalid token response from GitHub")
    if data.get("error"):
        desc = data.get("error_description")
        err = data.get("error")
        snippet = f"{err}: {desc}" if desc else str(err)
        _LOG.warning(
            "github_token_exchange_rejected",
            detail=str(snippet)[:280],
        )
        raise GithubOAuthProviderError("Token exchange rejected by GitHub")
    return data


async def fetch_user(access_token: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                GITHUB_API_USER,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            out = response.json()
    except httpx.HTTPStatusError as e:
        snippet = _github_error_snippet(e)
        _LOG.warning(
            "github_user_http_error",
            status_code=e.response.status_code,
            detail=snippet,
        )
        raise GithubOAuthProviderError("User profile request failed") from e
    except httpx.RequestError as e:
        raise GithubOAuthProviderError("User profile request failed") from e
    if not isinstance(out, dict):
        raise GithubOAuthProviderError("Invalid user response from GitHub")
    return out


async def fetch_user_emails(access_token: str) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                GITHUB_API_USER_EMAILS,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            out = response.json()
    except httpx.HTTPStatusError as e:
        snippet = _github_error_snippet(e)
        _LOG.warning(
            "github_user_emails_http_error",
            status_code=e.response.status_code,
            detail=snippet,
        )
        raise GithubOAuthProviderError("User emails request failed") from e
    except httpx.RequestError as e:
        raise GithubOAuthProviderError("User emails request failed") from e
    if not isinstance(out, list):
        raise GithubOAuthProviderError("Invalid emails response from GitHub")
    return out


def github_provider_user_id(user: dict[str, Any]) -> str:
    gid = user.get("id")
    if gid is None:
        raise GithubOAuthProviderError("GitHub user id missing")
    return str(gid)


def pick_verified_login_email(
    user: dict[str, Any],
    emails: list[dict[str, Any]],
) -> str | None:
    """
    Prefer a verified email. Many accounts hide public email; the emails
    endpoint (``user:email`` scope) is required for reliable resolution.
    """
    primary_verified: str | None = None
    any_verified: str | None = None
    for row in emails:
        if not isinstance(row, dict):
            continue
        addr = row.get("email")
        if not addr or not isinstance(addr, str) or not addr.strip():
            continue
        if not row.get("verified"):
            continue
        if row.get("primary"):
            primary_verified = addr.strip().lower()
            break
        if any_verified is None:
            any_verified = addr.strip().lower()

    if primary_verified:
        return primary_verified
    if any_verified:
        return any_verified

    # Legacy: public email on user object (often null); do not trust without verified flag from API.
    public = user.get("email")
    if isinstance(public, str) and public.strip():
        for row in emails:
            if not isinstance(row, dict):
                continue
            if row.get("email", "").strip().lower() == public.strip().lower() and row.get("verified"):
                return public.strip().lower()
    return None
