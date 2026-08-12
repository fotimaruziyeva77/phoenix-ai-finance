"""Authentication use-cases (register, login, refresh with server-side sessions, token resolution)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.security.token_errors import TokenExpiredError, TokenInvalidError, TokenTypeError
from app.lib.email_normalize import normalize_email
from app.lib.refresh_token_hash import hash_refresh_token, refresh_tokens_equal
from app.models.enums import UserRole
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.repositories.refresh_session_repository import RefreshSessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthSessionResponse, RefreshSessionRead
from app.schemas.user import TokenResponse, UserCreate, UserRead, UserUpdate
from app.services.auth_exceptions import (
    EmailAlreadyRegisteredError,
    EmailAlreadyVerifiedError,
    EmailServiceUnavailableError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
    InvalidSessionError,
    InvalidVerificationTokenError,
    NotAuthenticatedError,
    PasswordTooWeakError,
    RefreshTokenExpiredError,
    RefreshTokenReuseDetectedError,
    RefreshTokenRevokedError,
    TokenExpiredAuthError,
)
from app.services.email_service import EmailService

from app.services.refresh_session_constants import (
    REVOKE_REASON_FAMILY_INVALIDATED,
    REVOKE_REASON_LOGOUT,
    REVOKE_REASON_LOGOUT_ALL,
    REVOKE_REASON_ROTATED,
    REVOKE_REASON_REUSE_DETECTED,
)

_LOG = get_logger(__name__)


def _access_ttl_seconds(settings: Settings) -> int:
    return int(settings.jwt_access_token_expire_minutes * 60)


def _user_to_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_repo: RefreshSessionRepository,
        settings: Settings,
        email_service: EmailService | None = None,
    ) -> None:
        self._repo = user_repo
        self._refresh = refresh_repo
        self._settings = settings
        self._email = email_service

    @property
    def settings(self) -> Settings:
        """Settings snapshot (OAuth services need provider client configuration)."""
        return self._settings

    @property
    def user_repository(self) -> UserRepository:
        """Exposed for :mod:`app.services.oauth_resolution` (same DB session as refresh rows)."""
        return self._repo

    def _refresh_expiry(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=self._settings.jwt_refresh_token_expire_days)

    async def create_session_for_user(
        self,
        user: User,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> AuthSessionResponse:
        """
        Issue access + refresh JWTs and persist a new refresh session (new family).

        Commits the shared SQLAlchemy session.
        """
        if not user.is_active:
            raise InactiveUserError()

        family_id = uuid.uuid4()
        jti = str(uuid.uuid4())
        refresh_raw = create_refresh_token(
            user.id,
            settings=self._settings,
            jti=jti,
            family_id=family_id,
        )
        now = datetime.now(UTC)
        expires_at = self._refresh_expiry()
        row = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=family_id,
            jti=jti,
            token_hash=hash_refresh_token(refresh_raw),
            issued_at=now,
            expires_at=expires_at,
            rotated_from_jti=None,
            revoked_at=None,
            revoke_reason=None,
            device_info=device_info,
            ip_address=(client_ip or None)[:64] if client_ip else None,
            user_agent=user_agent,
        )
        await self._refresh.insert_session(row)
        access = create_access_token(
            user.id,
            user.role.value,
            user.email,
            settings=self._settings,
        )
        await self._repo.commit()
        return AuthSessionResponse(
            auth_transport="bearer",
            user=_user_to_read(user),
            access_token=access,
            refresh_token=refresh_raw,
            expires_in=_access_ttl_seconds(self._settings),
            csrf_token=None,
        )

    async def register(
        self,
        data: UserCreate,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> AuthSessionResponse:
        email = normalize_email(str(data.email))
        if await self._repo.get_by_email(email):
            raise EmailAlreadyRegisteredError()

        pwd_hash = hash_password(data.password)
        try:
            user = await self._repo.create_email_password_user(
                email=email,
                password_hash=pwd_hash,
                full_name=data.full_name,
                role=UserRole.customer_admin,
            )
        except IntegrityError:
            raise EmailAlreadyRegisteredError() from None

        session = await self.create_session_for_user(
            user,
            client_ip=client_ip,
            user_agent=user_agent,
            device_info=device_info,
        )
        # Send verification email in background (fire-and-forget, never blocks login)
        if self._email is not None:
            try:
                await self._email.send_verification_email(
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                )
            except Exception:
                _LOG.warning("register_verification_email_failed", user_id=str(user.id))
        return session

    async def login(
        self,
        email: str,
        password: str,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> AuthSessionResponse:
        user = await self._repo.get_by_email(normalize_email(email))
        if user is None or not user.password_hash:
            raise InvalidCredentialsError()
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()

        return await self.create_session_for_user(
            user,
            client_ip=client_ip,
            user_agent=user_agent,
            device_info=device_info,
        )

    async def refresh(
        self,
        refresh_token: str,
        *,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse:
        raw = (refresh_token or "").strip()
        try:
            payload = decode_token(
                raw,
                settings=self._settings,
                expected_token_type="refresh",
            )
        except TokenExpiredError as e:
            raise RefreshTokenExpiredError() from e
        except (TokenInvalidError, TokenTypeError) as e:
            raise InvalidRefreshTokenError() from e

        jti = payload.get("jti")
        if not isinstance(jti, str) or not jti.strip():
            raise InvalidRefreshTokenError()

        row = await self._refresh.get_by_jti(jti.strip())
        if row is None:
            raise InvalidRefreshTokenError()

        if not refresh_tokens_equal(raw, row.token_hash):
            raise InvalidRefreshTokenError()

        now = datetime.now(UTC)
        if row.expires_at <= now:
            raise RefreshTokenExpiredError()

        if row.revoked_at is not None:
            if row.revoke_reason == REVOKE_REASON_ROTATED:
                await self._refresh.revoke_family_active_sessions(
                    row.family_id,
                    revoked_at=now,
                    reason=REVOKE_REASON_FAMILY_INVALIDATED,
                )
                await self._repo.commit()
                _LOG.warning(
                    "refresh_token_reuse_detected",
                    user_id=str(row.user_id),
                    family_id=str(row.family_id),
                    jti=jti[:12] + "…",
                )
                raise RefreshTokenReuseDetectedError()
            raise RefreshTokenRevokedError()

        user = await self._repo.get_by_id(row.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        new_jti = str(uuid.uuid4())
        new_refresh_raw = create_refresh_token(
            user.id,
            settings=self._settings,
            jti=new_jti,
            family_id=row.family_id,
        )
        new_expires = self._refresh_expiry()
        new_row = RefreshSession(
            id=uuid.uuid4(),
            user_id=user.id,
            family_id=row.family_id,
            jti=new_jti,
            token_hash=hash_refresh_token(new_refresh_raw),
            issued_at=now,
            expires_at=new_expires,
            rotated_from_jti=row.jti,
            revoked_at=None,
            revoke_reason=None,
            device_info=device_info if device_info is not None else row.device_info,
            ip_address=(client_ip or row.ip_address or "")[:64] if (client_ip or row.ip_address) else None,
            user_agent=user_agent if user_agent is not None else row.user_agent,
        )

        try:
            await self._refresh.revoke_session(
                row.id,
                revoked_at=now,
                reason=REVOKE_REASON_ROTATED,
            )
            await self._refresh.insert_session(new_row)
            access = create_access_token(
                user.id,
                user.role.value,
                user.email,
                settings=self._settings,
            )
            await self._repo.commit()
        except Exception:
            await self._repo.rollback()
            raise

        return TokenResponse(
            auth_transport="bearer",
            access_token=access,
            refresh_token=new_refresh_raw,
            expires_in=_access_ttl_seconds(self._settings),
            csrf_token=None,
        )

    async def list_sessions(self, user: User) -> list[RefreshSessionRead]:
        rows = await self._refresh.list_active_sessions_for_user(user.id)
        return [RefreshSessionRead.model_validate(r) for r in rows]

    async def logout_current_refresh(self, refresh_token: str) -> None:
        raw = (refresh_token or "").strip()
        try:
            payload = decode_token(
                raw,
                settings=self._settings,
                expected_token_type="refresh",
            )
        except (TokenExpiredError, TokenInvalidError, TokenTypeError):
            raise InvalidSessionError("Invalid refresh token") from None

        jti = payload.get("jti")
        if not isinstance(jti, str) or not jti.strip():
            raise InvalidSessionError()

        row = await self._refresh.get_by_jti(jti.strip())
        if row is None or not refresh_tokens_equal(raw, row.token_hash):
            raise InvalidSessionError()

        now = datetime.now(UTC)
        if row.revoked_at is not None:
            return

        await self._refresh.revoke_session(row.id, revoked_at=now, reason=REVOKE_REASON_LOGOUT)
        await self._repo.commit()

    async def logout_all_refresh(self, user: User) -> None:
        now = datetime.now(UTC)
        await self._refresh.revoke_all_active_for_user(
            user.id,
            revoked_at=now,
            reason=REVOKE_REASON_LOGOUT_ALL,
        )
        await self._repo.commit()

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    async def send_verification_email(self, user: User) -> None:
        """Re-send the email verification link. Raises if email service is not configured."""
        if self._email is None:
            raise EmailServiceUnavailableError()
        if user.is_verified:
            raise EmailAlreadyVerifiedError()
        await self._email.send_verification_email(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
        )

    async def verify_email(self, token: str) -> User:
        """
        Consume a verification token and mark the user as verified.
        Sends a welcome email on success.

        Raises :exc:`InvalidVerificationTokenError` when the token is
        missing, expired, or already used.
        """
        if self._email is None:
            raise EmailServiceUnavailableError()

        user_id = await self._email.consume_verification_token(token)
        if user_id is None:
            raise InvalidVerificationTokenError()

        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise InvalidVerificationTokenError()

        if not user.is_verified:
            # Read scalars before commit — after commit the ORM object is expired
            # and attribute access would trigger a synchronous lazy-load in an
            # async context (MissingGreenlet).
            _uid = user.id
            _email = user.email
            _full_name = user.full_name
            user.is_verified = True
            await self._repo.commit()
            _LOG.info("email_verified", user_id=str(_uid))
            # Send welcome email (best-effort)
            try:
                await self._email.send_welcome_email(
                    email=_email,
                    full_name=_full_name,
                )
            except Exception:
                pass
            # Re-fetch so callers get a live, non-expired ORM object.
            refreshed = await self._repo.get_by_id(_uid)
            if refreshed is None:
                raise InvalidVerificationTokenError()
            return refreshed

        return user

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def forgot_password(self, email: str) -> None:
        """
        Send a password-reset email **if** the account exists.

        Deliberately does not raise when the email is unknown (prevents
        account enumeration).
        """
        if self._email is None:
            raise EmailServiceUnavailableError()

        user = await self._repo.get_by_email(normalize_email(email))
        if user is None or not user.is_active:
            # Silently succeed to prevent enumeration
            _LOG.debug("forgot_password_user_not_found_or_inactive")
            return
        if not user.password_hash:
            # OAuth-only account — can't reset a non-existent password
            _LOG.debug("forgot_password_oauth_only_account")
            return

        await self._email.send_password_reset_email(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        """
        Consume a password-reset token and update the user's password.

        Raises :exc:`InvalidPasswordResetTokenError` on bad/expired token.
        Raises :exc:`PasswordTooWeakError` when ``new_password`` is too short.
        """
        if self._email is None:
            raise EmailServiceUnavailableError()

        if len(new_password) < 8:
            raise PasswordTooWeakError()

        user_id = await self._email.consume_password_reset_token(token)
        if user_id is None:
            raise InvalidPasswordResetTokenError()

        user = await self._repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidPasswordResetTokenError()

        user.password_hash = hash_password(new_password)
        await self._repo.commit()
        _LOG.info("password_reset_success", user_id=str(user.id))

        # Revoke all existing refresh sessions for security
        from datetime import UTC, datetime

        from app.services.refresh_session_constants import REVOKE_REASON_LOGOUT_ALL

        await self._refresh.revoke_all_active_for_user(
            user.id,
            revoked_at=datetime.now(UTC),
            reason=REVOKE_REASON_LOGOUT_ALL,
        )
        await self._repo.commit()

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """
        Change an authenticated user's password.

        Raises :exc:`OAuthOnlyAccountError` when the user has no password hash.
        Raises :exc:`InvalidCurrentPasswordError` when current password is wrong.
        Raises :exc:`PasswordTooWeakError` when new password is too short.
        """
        from app.services.auth_exceptions import (
            InvalidCurrentPasswordError,
            OAuthOnlyAccountError,
        )

        # OAuth-only accounts don't have a password
        if not user.password_hash:
            raise OAuthOnlyAccountError()

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise InvalidCurrentPasswordError()

        # Validate new password strength
        if len(new_password) < 8:
            raise PasswordTooWeakError()

        # Update password
        user.password_hash = hash_password(new_password)
        await self._repo.commit()
        _LOG.info("password_changed", user_id=str(user.id))

    async def update_me(self, user: User, data: UserUpdate) -> User:
        """Update mutable profile fields for the authenticated user."""
        await self._repo.update_profile(user, full_name=data.full_name)
        await self._repo.commit()
        return user

    async def delete_account(self, user: User) -> None:
        """Permanently delete a user account and all related data (GDPR right to erasure).

        CASCADE foreign keys handle bots, conversations, leads, knowledge files,
        subscriptions, sessions, widget configs, etc. External services (Stripe,
        MinIO, Telegram) should be cleaned up by the caller before invoking this.
        """
        _LOG.info("account_deletion_started", user_id=str(user.id), email=user.email)
        await self._repo.delete(user)
        await self._repo.commit()
        _LOG.info("account_deletion_completed", user_id=str(user.id))

    async def get_user_for_access_token(self, token: str | None) -> User:
        if not token:
            _LOG.warning("auth_access_token_failed", reason="missing_token")
            raise NotAuthenticatedError()

        try:
            payload = decode_token(
                token,
                settings=self._settings,
                expected_token_type="access",
            )
        except TokenExpiredError as e:
            _LOG.warning("auth_access_token_failed", reason="token_expired")
            raise TokenExpiredAuthError() from e
        except (TokenInvalidError, TokenTypeError) as e:
            detail = (str(e) or "").strip()[:160] or None
            _LOG.warning(
                "auth_access_token_failed",
                reason="token_invalid_or_wrong_type",
                detail=detail,
            )
            raise NotAuthenticatedError() from e

        try:
            uid = uuid.UUID(str(payload["sub"]))
        except (ValueError, TypeError):
            _LOG.warning("auth_access_token_failed", reason="invalid_sub_claim")
            raise NotAuthenticatedError() from None

        user = await self._repo.get_by_id(uid)
        if user is None:
            log_kw: dict[str, object] = {"reason": "user_id_not_in_database"}
            if not self._settings.deploy_environment_is_strict:
                log_kw["sub_user_id"] = str(uid)
            _LOG.warning("auth_access_token_failed", **log_kw)
            raise NotAuthenticatedError()
        if not user.is_active:
            inactive_kw: dict[str, object] = {"reason": "inactive_user"}
            if not self._settings.deploy_environment_is_strict:
                inactive_kw["sub_user_id"] = str(uid)
            _LOG.warning("auth_access_token_failed", **inactive_kw)
            raise InactiveUserError()
        return user
