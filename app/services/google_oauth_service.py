"""Google OAuth login: authorize URL, callback handling, one-time exchange for JWT session."""

from __future__ import annotations

from urllib.parse import urlencode

from app.core.logging import get_logger
from app.core.auth_audit import audit_oauth_callback_redirect
from app.integrations.google_idp import (
    GOOGLE_AUTHORIZE_URL,
    exchange_authorization_code,
    fetch_userinfo,
)
from app.integrations.oauth_exchange_store import OAuthExchangeStore
from app.integrations.oauth_frontend_errors import frontend_oauth_error_url
from app.integrations.oauth_redirect import append_oauth_query_params
from app.integrations.oauth_state import create_google_oauth_state, verify_google_oauth_state
from app.lib.email_normalize import normalize_email
from app.models.enums import OAuthProvider
from app.schemas.auth import AuthSessionResponse
from app.services.auth_exceptions import (
    AuthServiceError,
    GoogleEmailNotVerifiedError,
    GoogleOAuthInvalidStateError,
    GoogleOAuthLinkConflictError,
    GoogleOAuthNotConfiguredError,
    GoogleOAuthProviderError,
)
from app.services.auth_service import AuthService
from app.services.oauth_exchange_consume import consume_oauth_exchange_code
from app.services.oauth_resolution import resolve_oauth_login

_LOG = get_logger(__name__)

GOOGLE_OAUTH_SCOPES = "openid email profile"


class GoogleOAuthService:
    def __init__(
        self,
        auth_service: AuthService,
        exchange_store: OAuthExchangeStore,
    ) -> None:
        self._auth = auth_service
        self._store = exchange_store

    def _require_google_client_config(self) -> tuple[str, str, str]:
        s = self._auth.settings
        cid = s.google_oauth_client_id
        secret = s.google_oauth_client_secret
        redirect_uri = s.google_oauth_redirect_uri
        if not cid or not secret or not redirect_uri:
            missing = [
                name
                for name, val in (
                    ("APP_GOOGLE_OAUTH_CLIENT_ID (or GOOGLE_CLIENT_ID)", cid),
                    ("APP_GOOGLE_OAUTH_CLIENT_SECRET (or GOOGLE_CLIENT_SECRET)", secret),
                    ("APP_GOOGLE_OAUTH_REDIRECT_URI (or GOOGLE_OAUTH_REDIRECT_URI)", redirect_uri),
                )
                if not val
            ]
            raise GoogleOAuthNotConfiguredError(
                "Google OAuth is not fully configured. Set: " + ", ".join(missing) + ". "
                "Redirect URI must match the backend callback URL registered in Google Cloud Console."
            )
        return cid, secret, redirect_uri

    def _require_frontend_redirect(self) -> str:
        base = self._auth.settings.frontend_oauth_redirect_url
        if not base:
            raise GoogleOAuthNotConfiguredError(
                "Frontend OAuth redirect URL is not configured",
            )
        return str(base).strip().rstrip("/")

    def build_authorize_url(self) -> str:
        client_id, _, redirect_uri = self._require_google_client_config()
        state = create_google_oauth_state(self._auth.settings)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_OAUTH_SCOPES,
            "state": state,
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"

    def _redirect_error(self, *, code: str, detail: str | None = None) -> str:
        return frontend_oauth_error_url(
            self._require_frontend_redirect(),
            oauth_error_code=code,
            detail=detail,
            expose_error_details=self._auth.settings.expose_error_details,
        )

    async def complete_callback_redirect_url(
        self,
        *,
        code: str | None,
        state: str | None,
        provider_error: str | None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        frontend = self._require_frontend_redirect()

        if provider_error:
            err_code = (
                "google_oauth_denied" if provider_error == "access_denied" else "google_oauth_error"
            )
            url = frontend_oauth_error_url(frontend, oauth_error_code=err_code)
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        if not code or not str(code).strip():
            url = frontend_oauth_error_url(frontend, oauth_error_code="google_oauth_missing_code")
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        try:
            verify_google_oauth_state(state, self._auth.settings)
        except GoogleOAuthInvalidStateError as e:
            url = self._redirect_error(code=e.code, detail=e.message)
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        client_id, client_secret, redirect_uri = self._require_google_client_config()
        try:
            token_payload = await exchange_authorization_code(
                client_id=client_id,
                client_secret=client_secret,
                code=str(code).strip(),
                redirect_uri=redirect_uri,
            )
        except GoogleOAuthProviderError as e:
            url = self._redirect_error(
                code="google_token_exchange_failed",
                detail=e.message if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        access = token_payload.get("access_token")
        if not access or not isinstance(access, str):
            url = self._redirect_error(
                code="google_token_exchange_failed",
                detail="Missing access_token in Google token response"
                if self._auth.settings.expose_error_details
                else None,
            )
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        try:
            profile = await fetch_userinfo(access)
        except GoogleOAuthProviderError as e:
            url = self._redirect_error(
                code="google_userinfo_failed",
                detail=e.message if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        try:
            session = await self._resolve_profile_to_session(
                profile,
                client_ip=client_ip,
                user_agent=user_agent,
            )
        except AuthServiceError as e:
            url = self._redirect_error(code=e.code, detail=e.message)
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url
        except Exception as e:
            _LOG.exception("google_oauth_resolve_unexpected", client_ip=client_ip)
            url = self._redirect_error(
                code="google_oauth_internal_error",
                detail=str(e) if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
            return url

        exchange_code = self._store.put(session.model_dump_json(), ttl_seconds=120)
        url = append_oauth_query_params(frontend, {"oauth_exchange_code": exchange_code})
        audit_oauth_callback_redirect(provider="google", client_ip=client_ip, redirect_url=url)
        return url

    async def _resolve_profile_to_session(
        self,
        profile: dict,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSessionResponse:
        sub = profile.get("sub")
        email_raw = profile.get("email")
        email_verified = profile.get("email_verified")
        name = profile.get("name")

        if not sub or not isinstance(sub, str):
            raise GoogleOAuthProviderError("Invalid identity from Google")
        if not email_raw or not isinstance(email_raw, str):
            raise GoogleOAuthProviderError("Google did not return an email")
        if email_verified is not True:
            raise GoogleEmailNotVerifiedError()

        email = normalize_email(email_raw)
        name_str = name.strip() if isinstance(name, str) and name.strip() else None

        return await resolve_oauth_login(
            self._auth,
            provider=OAuthProvider.google,
            provider_user_id=sub,
            email=email,
            full_name=name_str,
            link_conflict_error=GoogleOAuthLinkConflictError,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    def consume_exchange_code(self, exchange_code: str) -> AuthSessionResponse:
        return consume_oauth_exchange_code(self._store, exchange_code)
