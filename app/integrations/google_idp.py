"""Google OAuth 2.0 token and OpenID userinfo (authorization code flow)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.auth_exceptions import GoogleOAuthProviderError

_LOG = get_logger(__name__)

def _google_oauth_error_snippet(exc: httpx.HTTPStatusError) -> str:
    """Short, non-secret summary from Google token/userinfo error JSON (for logs / dev details)."""
    try:
        body = exc.response.json()
        if isinstance(body, dict):
            err = body.get("error")
            desc = body.get("error_description")
            if err and desc:
                return f"{err}: {str(desc)[:280]}"
            if err:
                return str(err)[:200]
    except Exception:
        pass
    text = (exc.response.text or "").strip()
    return text[:200] if text else ""


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


async def exchange_authorization_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    form = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    _LOG.info(
        "google_token_exchange_attempt",
        redirect_uri=redirect_uri,
        client_id_prefix=client_id[:8] + "..." if len(client_id) > 8 else client_id,
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        snippet = _google_oauth_error_snippet(e)
        is_redirect_uri_mismatch = (
            "redirect_uri_mismatch" in snippet.lower()
            or "redirect_uri" in snippet.lower()
        )
        _LOG.warning(
            "google_token_exchange_http_error",
            status_code=e.response.status_code,
            detail=snippet,
            redirect_uri_used=redirect_uri,
            redirect_uri_mismatch=is_redirect_uri_mismatch,
            hint=(
                "The redirect_uri sent to Google does not match what is registered "
                "in Google Cloud Console. Check GOOGLE_OAUTH_REDIRECT_URI in your .env "
                "against the Authorized redirect URIs in the OAuth 2.0 client settings."
            ) if is_redirect_uri_mismatch else None,
        )
        msg = f"Token exchange failed ({snippet})" if snippet else "Token exchange failed"
        raise GoogleOAuthProviderError(msg) from e
    except httpx.RequestError as e:
        raise GoogleOAuthProviderError("Token exchange request failed") from e


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        snippet = _google_oauth_error_snippet(e)
        _LOG.warning(
            "google_userinfo_http_error",
            status_code=e.response.status_code,
            detail=snippet,
        )
        raise GoogleOAuthProviderError("User info request failed") from e
    except httpx.RequestError as e:
        raise GoogleOAuthProviderError("User info request failed") from e
