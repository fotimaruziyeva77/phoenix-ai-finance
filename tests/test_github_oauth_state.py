"""GitHub OAuth state JWT (CSRF)."""

from __future__ import annotations

from app.core.config import Settings
from app.integrations.oauth_state import create_github_oauth_state, verify_github_oauth_state
from app.services.auth_exceptions import GithubOAuthInvalidStateError


def test_github_oauth_state_round_trip() -> None:
    settings = Settings(
        jwt_secret_key="x" * 32,
        jwt_algorithm="HS256",
        environment="local",
    )
    token = create_github_oauth_state(settings)
    verify_github_oauth_state(token, settings)


def test_github_oauth_state_rejects_wrong_secret() -> None:
    a = Settings(jwt_secret_key="a" * 32, jwt_algorithm="HS256", environment="local")
    b = Settings(jwt_secret_key="b" * 32, jwt_algorithm="HS256", environment="local")
    token = create_github_oauth_state(a)
    try:
        verify_github_oauth_state(token, b)
    except GithubOAuthInvalidStateError:
        return
    raise AssertionError("expected GithubOAuthInvalidStateError")


def test_google_state_rejects_github_flow_token() -> None:
    """Cross-provider reuse of ``state`` must fail verification."""
    from app.integrations.oauth_state import verify_google_oauth_state
    from app.services.auth_exceptions import GoogleOAuthInvalidStateError

    settings = Settings(jwt_secret_key="x" * 32, jwt_algorithm="HS256", environment="local")
    token = create_github_oauth_state(settings)
    try:
        verify_google_oauth_state(token, settings)
    except GoogleOAuthInvalidStateError:
        return
    raise AssertionError("expected GoogleOAuthInvalidStateError for wrong flow")
