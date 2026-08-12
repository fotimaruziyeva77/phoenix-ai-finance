"""Domain errors for auth flows (mapped to HTTP by ``exception_handlers``)."""

from __future__ import annotations

from typing import ClassVar


class AuthServiceError(Exception):
    """Base error for auth service; carries stable API codes."""

    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "auth_error"
    default_message: ClassVar[str] = "Authentication failed"

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class EmailAlreadyRegisteredError(AuthServiceError):
    status_code = 409
    code = "email_already_registered"
    default_message = "An account with this email already exists"


class InvalidCredentialsError(AuthServiceError):
    status_code = 401
    code = "invalid_credentials"
    default_message = "Invalid email or password"


class InactiveUserError(AuthServiceError):
    status_code = 403
    code = "inactive_user"
    default_message = "This account is disabled"


class InvalidRefreshTokenError(AuthServiceError):
    status_code = 401
    code = "invalid_refresh_token"
    default_message = "Invalid or expired refresh token"


class RefreshTokenExpiredError(AuthServiceError):
    status_code = 401
    code = "refresh_token_expired"
    default_message = "Refresh token has expired"


class RefreshTokenRevokedError(AuthServiceError):
    status_code = 401
    code = "refresh_token_revoked"
    default_message = "Refresh token has been revoked"


class RefreshTokenReuseDetectedError(AuthServiceError):
    """A previously rotated refresh token was presented again — family invalidated."""

    status_code = 401
    code = "refresh_token_reuse_detected"
    default_message = "Refresh token reuse detected; sign in again"


class InvalidSessionError(AuthServiceError):
    status_code = 400
    code = "invalid_session"
    default_message = "Session is invalid or not found"


class RefreshTokenRequiredError(AuthServiceError):
    """Neither JSON body nor cookie supplied a refresh token (cookie auth mode uses HttpOnly cookie)."""

    status_code = 422
    code = "refresh_token_required"
    default_message = "refresh_token is required (JSON body or bf_refresh cookie)"


class CsrfValidationError(AuthServiceError):
    status_code = 403
    code = "csrf_validation_failed"
    default_message = "CSRF validation failed; send X-CSRF-Token matching the bf_csrf cookie"


class NotAuthenticatedError(AuthServiceError):
    status_code = 401
    code = "not_authenticated"
    default_message = "Not authenticated"


class TokenExpiredAuthError(AuthServiceError):
    status_code = 401
    code = "token_expired"
    default_message = "Access token has expired"


class JwtSecretNotConfiguredError(AuthServiceError):
    """JWT secret missing (tokens, OAuth ``state`` signing, etc.)."""

    status_code = 503
    code = "jwt_secret_not_configured"
    default_message = "JWT secret is not configured on this server"


class GoogleOAuthNotConfiguredError(AuthServiceError):
    status_code = 503
    code = "google_oauth_not_configured"
    default_message = "Google sign-in is not configured on this server"


class GoogleOAuthInvalidStateError(AuthServiceError):
    status_code = 400
    code = "google_oauth_invalid_state"
    default_message = "Invalid or expired OAuth state"


class GoogleOAuthProviderError(AuthServiceError):
    status_code = 502
    code = "google_oauth_provider_error"
    default_message = "Could not complete sign-in with Google"


class GoogleEmailNotVerifiedError(AuthServiceError):
    status_code = 403
    code = "google_email_not_verified"
    default_message = "Google account email is not verified"


class GoogleOAuthLinkConflictError(AuthServiceError):
    status_code = 409
    code = "google_oauth_link_conflict"
    default_message = "This Google account cannot be linked to the existing user"


class OAuthExchangeInvalidError(AuthServiceError):
    status_code = 401
    code = "oauth_exchange_invalid"
    default_message = "Invalid or expired OAuth exchange code"


class OAuthInvalidStateError(AuthServiceError):
    """Generic CSRF/state failure (providers may wrap for stable redirect codes)."""

    status_code = 400
    code = "oauth_invalid_state"
    default_message = "Invalid or expired OAuth state"


class GithubOAuthNotConfiguredError(AuthServiceError):
    status_code = 503
    code = "github_oauth_not_configured"
    default_message = "GitHub sign-in is not configured on this server"


class GithubOAuthInvalidStateError(AuthServiceError):
    status_code = 400
    code = "github_oauth_invalid_state"
    default_message = "Invalid or expired OAuth state"


class GithubOAuthProviderError(AuthServiceError):
    status_code = 502
    code = "github_oauth_provider_error"
    default_message = "Could not complete sign-in with GitHub"


class GithubOAuthEmailUnavailableError(AuthServiceError):
    status_code = 403
    code = "github_oauth_email_unavailable"
    default_message = "GitHub did not provide a verified email for this account"


class GithubOAuthLinkConflictError(AuthServiceError):
    status_code = 409
    code = "github_oauth_link_conflict"
    default_message = "This GitHub account cannot be linked to the existing user"


class EmailAlreadyVerifiedError(AuthServiceError):
    status_code = 409
    code = "email_already_verified"
    default_message = "Email address is already verified"


class InvalidVerificationTokenError(AuthServiceError):
    status_code = 400
    code = "invalid_verification_token"
    default_message = "Verification token is invalid or has expired"


class InvalidPasswordResetTokenError(AuthServiceError):
    status_code = 400
    code = "invalid_password_reset_token"
    default_message = "Password reset token is invalid or has expired"


class EmailServiceUnavailableError(AuthServiceError):
    status_code = 503
    code = "email_service_unavailable"
    default_message = "Email service is not configured on this server"


class PasswordTooWeakError(AuthServiceError):
    status_code = 422
    code = "password_too_weak"
    default_message = "Password must be at least 8 characters long"


class InvalidCurrentPasswordError(AuthServiceError):
    status_code = 400
    code = "invalid_current_password"
    default_message = "Current password is incorrect"


class OAuthOnlyAccountError(AuthServiceError):
    status_code = 400
    code = "oauth_only_account"
    default_message = "This account uses social login and has no password to change"
