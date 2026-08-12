"""GitHub OAuth login: authorize URL, callback, one-time exchange for JWT session."""

from __future__ import annotations

from urllib.parse import urlencode

from app.core.logging import get_logger
from app.core.auth_audit import audit_oauth_callback_redirect
from app.integrations.github_idp import (
    GITHUB_AUTHORIZE_URL,
    exchange_authorization_code,
    fetch_user,
    fetch_user_emails,
    github_provider_user_id,
    pick_verified_login_email,
)
from app.integrations.oauth_exchange_store import OAuthExchangeStore
from app.integrations.oauth_frontend_errors import frontend_oauth_error_url
from app.integrations.oauth_redirect import append_oauth_query_params
from app.integrations.oauth_state import create_github_oauth_state, verify_github_oauth_state
from app.lib.email_normalize import normalize_email
from app.models.enums import OAuthProvider
from app.schemas.auth import AuthSessionResponse
from app.services.auth_exceptions import (
    AuthServiceError,
    GithubOAuthEmailUnavailableError,
    GithubOAuthInvalidStateError,
    GithubOAuthLinkConflictError,
    GithubOAuthNotConfiguredError,
    GithubOAuthProviderError,
)
from app.services.auth_service import AuthService
from app.services.oauth_exchange_consume import consume_oauth_exchange_code
from app.services.oauth_resolution import resolve_oauth_login

# read:user + user:email so we can list verified emails when the profile email is hidden.
_LOG = get_logger(__name__)

GITHUB_OAUTH_SCOPES = "read:user user:email"


class GithubOAuthService:
    def __init__(
        self,
        auth_service: AuthService,
        exchange_store: OAuthExchangeStore,
    ) -> None:
        self._auth = auth_service
        self._store = exchange_store

    def _require_github_client_config(self) -> tuple[str, str, str]:
        s = self._auth.settings
        cid = s.github_oauth_client_id
        secret = s.github_oauth_client_secret
        redirect_uri = s.github_oauth_redirect_uri
        if not cid or not secret or not redirect_uri:
            missing = [
                name
                for name, val in (
                    ("APP_GITHUB_OAUTH_CLIENT_ID (or GITHUB_CLIENT_ID)", cid),
                    ("APP_GITHUB_OAUTH_CLIENT_SECRET (or GITHUB_CLIENT_SECRET)", secret),
                    ("APP_GITHUB_OAUTH_REDIRECT_URI (or GITHUB_OAUTH_REDIRECT_URI)", redirect_uri),
                )
                if not val
            ]
            raise GithubOAuthNotConfiguredError(
                "GitHub OAuth is not fully configured. Set: " + ", ".join(missing) + ". "
                "Authorization callback URL must match this redirect URI in the GitHub OAuth App settings."
            )
        return cid, secret, redirect_uri

    def _require_frontend_redirect(self) -> str:
        base = self._auth.settings.frontend_oauth_redirect_url
        if not base:
            raise GithubOAuthNotConfiguredError(
                "Frontend OAuth redirect URL is not configured",
            )
        return str(base).strip().rstrip("/")

    def build_authorize_url(self) -> str:
        client_id, _, redirect_uri = self._require_github_client_config()
        state = create_github_oauth_state(self._auth.settings)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": GITHUB_OAUTH_SCOPES,
            "state": state,
            "allow_signup": "true",
        }
        return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

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
                "github_oauth_denied" if provider_error == "access_denied" else "github_oauth_error"
            )
            url = frontend_oauth_error_url(frontend, oauth_error_code=err_code)
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        if not code or not str(code).strip():
            url = frontend_oauth_error_url(frontend, oauth_error_code="github_oauth_missing_code")
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        try:
            verify_github_oauth_state(state, self._auth.settings)
        except GithubOAuthInvalidStateError as e:
            url = self._redirect_error(code=e.code, detail=e.message)
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        client_id, client_secret, redirect_uri = self._require_github_client_config()
        try:
            token_payload = await exchange_authorization_code(
                client_id=client_id,
                client_secret=client_secret,
                code=str(code).strip(),
                redirect_uri=redirect_uri,
            )
        except GithubOAuthProviderError as e:
            url = self._redirect_error(
                code="github_token_exchange_failed",
                detail=e.message if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        access = token_payload.get("access_token")
        if not access or not isinstance(access, str):
            url = self._redirect_error(code="github_token_exchange_failed")
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        try:
            user = await fetch_user(access)
            emails = await fetch_user_emails(access)
        except GithubOAuthProviderError as e:
            url = self._redirect_error(
                code="github_userinfo_failed",
                detail=e.message if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        try:
            session = await self._resolve_github_to_session(
                user,
                emails,
                client_ip=client_ip,
                user_agent=user_agent,
            )
        except AuthServiceError as e:
            url = self._redirect_error(code=e.code, detail=e.message)
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url
        except Exception as e:
            _LOG.exception("github_oauth_resolve_unexpected", client_ip=client_ip)
            url = self._redirect_error(
                code="github_oauth_internal_error",
                detail=str(e) if self._auth.settings.expose_error_details else None,
            )
            audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
            return url

        exchange_code = self._store.put(session.model_dump_json(), ttl_seconds=120)
        url = append_oauth_query_params(frontend, {"oauth_exchange_code": exchange_code})
        audit_oauth_callback_redirect(provider="github", client_ip=client_ip, redirect_url=url)
        return url

    async def _resolve_github_to_session(
        self,
        user: dict,
        emails: list,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSessionResponse:
        sub = github_provider_user_id(user)
        raw_email = pick_verified_login_email(user, emails)
        if not raw_email:
            raise GithubOAuthEmailUnavailableError()

        email = normalize_email(raw_email)
        name = user.get("name")
        login = user.get("login")
        if isinstance(name, str) and name.strip():
            full_name = name.strip()
        elif isinstance(login, str) and login.strip():
            full_name = login.strip()
        else:
            full_name = None

        return await resolve_oauth_login(
            self._auth,
            provider=OAuthProvider.github,
            provider_user_id=sub,
            email=email,
            full_name=full_name,
            link_conflict_error=GithubOAuthLinkConflictError,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    def consume_exchange_code(self, exchange_code: str) -> AuthSessionResponse:
        return consume_oauth_exchange_code(self._store, exchange_code)
