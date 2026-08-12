"""Auth endpoints (handlers delegate to ``AuthService``)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.auth_csrf import read_refresh_token_from_request
from app.api.auth_http import json_auth_session_response, json_token_response, merge_clear_cookies
from app.api.deps import (
    AuthServiceDep,
    BillingServiceDep,
    CurrentUser,
    CurrentUserOptional,
    DbSession,
    SettingsDep,
    rate_limit_auth_forgot_password,
    rate_limit_auth_login,
    rate_limit_auth_logout,
    rate_limit_auth_refresh,
    rate_limit_auth_register,
    rate_limit_auth_reset_password,
    require_csrf_if_cookie_auth,
)
from app.core.auth_audit import log_auth_event
from app.core.request_client import client_ip
from app.lib.email_normalize import email_domain
from app.schemas.auth import (
    AuthBootstrapResponse,
    AuthSessionResponse,
    RefreshSessionListResponse,
    SessionStatusResponse,
)
from app.schemas.user import LoginRequest, MeResponse, RefreshRequest, TokenResponse, UserCreate, UserRead, UserUpdate
from app.api.auth_openapi import (
    LIST_SESSIONS_OPENAPI_RESPONSES,
    LOGIN_OPENAPI_RESPONSES,
    LOGOUT_ALL_OPENAPI_RESPONSES,
    LOGOUT_CURRENT_OPENAPI_RESPONSES,
    LOGOUT_OPENAPI_RESPONSES,
    ME_OPENAPI_RESPONSES,
    REFRESH_OPENAPI_RESPONSES,
    REGISTER_OPENAPI_RESPONSES,
)
from app.services.auth_exceptions import (
    EmailAlreadyRegisteredError,
    EmailAlreadyVerifiedError,
    EmailServiceUnavailableError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidCurrentPasswordError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
    InvalidSessionError,
    InvalidVerificationTokenError,
    OAuthOnlyAccountError,
    PasswordTooWeakError,
    RefreshTokenExpiredError,
    RefreshTokenRequiredError,
    RefreshTokenReuseDetectedError,
    RefreshTokenRevokedError,
)
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic schemas (inline — small, auth-only)
# ---------------------------------------------------------------------------

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    pass  # authenticated endpoint — user comes from CurrentUser


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


def _client_user_agent(request: Request) -> str | None:
    ua = request.headers.get("user-agent")
    return ua if ua else None


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Create account (email/password)",
    response_model=AuthSessionResponse,
    responses=REGISTER_OPENAPI_RESPONSES,
)
async def register(
    request: Request,
    _: Annotated[None, Depends(rate_limit_auth_register)],
    body: UserCreate,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> JSONResponse:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    try:
        out = await auth_service.register(
            body,
            client_ip=ip,
            user_agent=_client_user_agent(request),
        )
        log_auth_event(
            "auth.register",
            outcome="success",
            client_ip=ip,
            user_id=out.user.id,
            role=out.user.role.value,
        )
        return json_auth_session_response(settings, out, status_code=status.HTTP_201_CREATED)
    except EmailAlreadyRegisteredError as e:
        log_auth_event(
            "auth.register",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
            email_domain=email_domain(str(body.email)),
        )
        raise


@router.post(
    "/login",
    summary="Obtain tokens with email and password",
    response_model=AuthSessionResponse,
    responses=LOGIN_OPENAPI_RESPONSES,
)
async def login(
    request: Request,
    _: Annotated[None, Depends(rate_limit_auth_login)],
    body: LoginRequest,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> JSONResponse:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    dom = email_domain(str(body.email))
    try:
        out = await auth_service.login(
            str(body.email),
            body.password,
            client_ip=ip,
            user_agent=_client_user_agent(request),
        )
        log_auth_event(
            "auth.login",
            outcome="success",
            client_ip=ip,
            user_id=out.user.id,
            role=out.user.role.value,
            email_domain=dom,
        )
        return json_auth_session_response(settings, out)
    except InvalidCredentialsError as e:
        log_auth_event(
            "auth.login",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
            email_domain=dom,
        )
        raise
    except InactiveUserError as e:
        log_auth_event(
            "auth.login",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
            email_domain=dom,
        )
        raise


@router.post(
    "/refresh",
    summary="Exchange refresh token for a new token pair",
    response_model=TokenResponse,
    responses=REFRESH_OPENAPI_RESPONSES,
)
async def refresh_tokens(
    request: Request,
    _: Annotated[None, Depends(rate_limit_auth_refresh)],
    __csrf: Annotated[None, Depends(require_csrf_if_cookie_auth)],
    body: RefreshRequest,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> JSONResponse:
    """
    Validates refresh JWT + DB row, rotates, revokes the old row. Cookie mode: refresh may be HttpOnly cookie.
    When cookie auth is enabled, send ``X-CSRF-Token`` matching ``bf_csrf``.
    """
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    rt = read_refresh_token_from_request(request, settings, body.refresh_token)
    if not rt:
        raise RefreshTokenRequiredError()
    try:
        out = await auth_service.refresh(
            rt,
            client_ip=ip,
            user_agent=_client_user_agent(request),
        )
        log_auth_event("auth.refresh", outcome="success", client_ip=ip)
        return json_token_response(settings, out)
    except (
        InvalidRefreshTokenError,
        RefreshTokenExpiredError,
        RefreshTokenRevokedError,
    ) as e:
        log_auth_event(
            "auth.refresh",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
        )
        raise
    except RefreshTokenReuseDetectedError as e:
        log_auth_event(
            "auth.refresh",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
            extra={"security_event": "refresh_token_reuse"},
        )
        raise


@router.get(
    "/session",
    summary="Whether a valid access token was supplied (optional auth)",
    response_model=SessionStatusResponse,
)
async def session_status(user: CurrentUserOptional) -> SessionStatusResponse:
    """Uses ``CurrentUserOptional`` — no error when the client omits ``Authorization``."""
    return SessionStatusResponse(authenticated=user is not None)


@router.get(
    "/bootstrap",
    response_model=AuthBootstrapResponse,
    summary="SPA hydration: auth state + user + CSRF hint (cookie or Bearer)",
)
async def auth_bootstrap(
    request: Request,
    user: CurrentUserOptional,
    settings: SettingsDep,
) -> AuthBootstrapResponse:
    if user is None:
        return AuthBootstrapResponse(authenticated=False, auth_transport="none", user=None, csrf_token=None)
    csrf: str | None = None
    transport: Literal["bearer", "cookie"] = "bearer"
    if settings.auth_cookie_enabled and request.cookies.get(settings.auth_access_cookie_name):
        transport = "cookie"
        csrf = request.cookies.get(settings.auth_csrf_cookie_name)
    return AuthBootstrapResponse(
        authenticated=True,
        auth_transport=transport,
        user=UserRead.model_validate(user),
        csrf_token=csrf,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current user profile",
    responses=ME_OPENAPI_RESPONSES,
)
async def me(user: CurrentUser) -> MeResponse:
    resp = MeResponse.model_validate(user)
    return resp.model_copy(update={"has_password": user.password_hash is not None})


@router.patch(
    "/me",
    response_model=MeResponse,
    summary="Update current user profile",
    responses=ME_OPENAPI_RESPONSES,
)
async def update_me(
    body: UserUpdate,
    user: CurrentUser,
    auth_service: AuthServiceDep,
) -> MeResponse:
    updated = await auth_service.update_me(user, body)
    resp = MeResponse.model_validate(updated)
    return resp.model_copy(update={"has_password": updated.password_hash is not None})


# ---------------------------------------------------------------------------
# Account deletion (GDPR right to erasure)
# ---------------------------------------------------------------------------


class DeleteAccountRequest(BaseModel):
    confirm: bool


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete your account and all associated data",
    description=(
        "Irreversible GDPR right-to-erasure action. Deletes your user record, bots, "
        "conversations, leads, knowledge files, subscriptions, and all other owned data. "
        "Send ``{\"confirm\": true}`` to proceed."
    ),
)
async def delete_me(
    body: DeleteAccountRequest,
    user: CurrentUser,
    auth_service: AuthServiceDep,
    billing_service: BillingServiceDep,
) -> None:
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set confirm=true to permanently delete your account.",
        )
    # Cancel Stripe subscription before deletion (best-effort)
    try:
        await billing_service.cancel_subscription_for_deletion(user)
    except Exception:
        pass  # Stripe failure shouldn't block account deletion
    await auth_service.delete_account(user)


# ---------------------------------------------------------------------------
# Data export (GDPR right of access / data portability)
# ---------------------------------------------------------------------------


class DataExportResponse(BaseModel):
    user: dict[str, Any]
    bots: list[dict[str, Any]]
    leads: list[dict[str, Any]]
    conversations_count: int
    subscription: dict[str, Any] | None
    exported_at: str


@router.get(
    "/me/export",
    response_model=DataExportResponse,
    summary="Export your personal data (GDPR data portability)",
    description=(
        "Returns a JSON snapshot of your user profile, bots, leads, and subscription. "
        "Conversation messages are counted but not included for size reasons."
    ),
)
async def export_my_data(
    user: CurrentUser,
    session: DbSession,
    billing_service: BillingServiceDep,
) -> DataExportResponse:
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from app.models.ai_foundation import Conversation
    from app.models.bot import Bot
    from app.models.lead import Lead

    # User profile
    user_data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }

    # Bots
    bots_result = await session.execute(
        select(Bot).where(Bot.owner_id == user.id)
    )
    bots_data = [
        {
            "id": str(b.id),
            "name": b.name,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bots_result.scalars().all()
    ]

    # Leads
    leads_result = await session.execute(
        select(Lead).where(Lead.owner_id == user.id)
    )
    leads_data = [
        {
            "id": str(lead.id),
            "name": lead.visitor_name,
            "email": lead.visitor_email,
            "status": lead.status,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        }
        for lead in leads_result.scalars().all()
    ]

    # Conversation count
    conv_count_result = await session.execute(
        select(func.count(Conversation.id)).where(Conversation.owner_id == user.id)
    )
    conv_count = int(conv_count_result.scalar_one() or 0)

    # Subscription
    sub_data = None
    try:
        plan_limits = await billing_service.get_plan_limits(user)
        sub = await billing_service.get_or_create_subscription(user)
        sub_data = {
            "plan_slug": sub.plan_slug.value if hasattr(sub.plan_slug, "value") else str(sub.plan_slug),
            "status": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "plan_name": plan_limits.name,
        }
    except Exception:
        pass

    return DataExportResponse(
        user=user_data,
        bots=bots_data,
        leads=leads_data,
        conversations_count=conv_count,
        subscription=sub_data,
        exported_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/sessions",
    response_model=RefreshSessionListResponse,
    summary="List active refresh sessions for the current user",
    responses=LIST_SESSIONS_OPENAPI_RESPONSES,
)
async def list_sessions(
    user: CurrentUser,
    auth_service: AuthServiceDep,
) -> RefreshSessionListResponse:
    items = await auth_service.list_sessions(user)
    return RefreshSessionListResponse(items=items)


@router.post(
    "/logout-current",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke the refresh session for this device (send current refresh token)",
    responses=LOGOUT_CURRENT_OPENAPI_RESPONSES,
)
async def logout_current(
    request: Request,
    _: Annotated[None, Depends(rate_limit_auth_logout)],
    __csrf: Annotated[None, Depends(require_csrf_if_cookie_auth)],
    body: RefreshRequest,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    rt = read_refresh_token_from_request(request, settings, body.refresh_token)
    if not rt:
        raise RefreshTokenRequiredError()
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        await auth_service.logout_current_refresh(rt)
        log_auth_event("auth.logout_current", outcome="success", client_ip=ip)
    except InvalidSessionError as e:
        log_auth_event(
            "auth.logout_current",
            outcome="failure",
            client_ip=ip,
            reason_code=e.code,
        )
        merge_clear_cookies(settings, resp)
        raise
    merge_clear_cookies(settings, resp)
    return resp


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke all refresh sessions for the current user",
    responses=LOGOUT_ALL_OPENAPI_RESPONSES,
)
async def logout_all(
    request: Request,
    user: CurrentUser,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    __csrf: Annotated[None, Depends(require_csrf_if_cookie_auth)],
) -> Response:
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    await auth_service.logout_all_refresh(user)
    log_auth_event(
        "auth.logout_all",
        outcome="success",
        client_ip=ip,
        user_id=user.id,
        role=user.role.value,
    )
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    merge_clear_cookies(settings, resp)
    return resp


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="End session (clear cookies; optional Bearer audit log)",
    responses=LOGOUT_OPENAPI_RESPONSES,
)
async def logout(
    request: Request,
    _: Annotated[None, Depends(rate_limit_auth_logout)],
    user: CurrentUserOptional,
    settings: SettingsDep,
    __csrf: Annotated[None, Depends(require_csrf_if_cookie_auth)],
) -> Response:
    """
    Clears auth cookies when cookie mode is on. For server-side refresh revocation use
    ``POST /auth/logout-current`` or ``POST /auth/logout-all``.
    """
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    merge_clear_cookies(settings, resp)
    if user is not None:
        log_auth_event(
            "auth.logout",
            outcome="success",
            client_ip=ip,
            user_id=user.id,
            role=user.role.value,
        )
    else:
        log_auth_event(
            "auth.logout",
            outcome="success",
            client_ip=ip,
            reason_code="no_bearer",
        )
    return resp


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Confirm email address with a verification token",
    response_model=UserRead,
)
async def verify_email(
    body: VerifyEmailRequest,
    auth_service: AuthServiceDep,
) -> UserRead:
    """
    Consume the one-time token sent to the user's inbox and mark the account
    as verified.  Returns the updated user object.

    Raises **400** when the token is missing, expired, or already used.
    """
    user = await auth_service.verify_email(body.token)
    return UserRead.model_validate(user)


@router.post(
    "/resend-verification",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Re-send the email verification link (authenticated)",
)
async def resend_verification(
    user: CurrentUser,
    auth_service: AuthServiceDep,
) -> Response:
    """
    Re-sends the verification email for the currently authenticated user.

    Raises **409** if the email is already verified.
    Raises **503** if email service is not configured.
    """
    await auth_service.send_verification_email(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Change password for the authenticated user",
)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: CurrentUser,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    """
    Change the authenticated user's password by verifying the current password.

    Raises **400** when the current password is incorrect or account is OAuth-only.
    Raises **422** when ``new_password`` is too short (< 8 chars).
    """
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    await auth_service.change_password(user, body.current_password, body.new_password)
    log_auth_event(
        "auth.change_password",
        outcome="success",
        client_ip=ip,
        user_id=str(user.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Request a password-reset email",
)
async def forgot_password(
    request: Request,
    _rl: Annotated[None, Depends(rate_limit_auth_forgot_password)],
    body: ForgotPasswordRequest,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    """
    Send a password-reset link to the given email address if an account exists.

    **Always returns 204** regardless of whether the address is registered
    (prevents account enumeration).

    Raises **503** if email service is not configured.
    """
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    await auth_service.forgot_password(str(body.email))
    log_auth_event("auth.forgot_password", outcome="success", client_ip=ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Set a new password using a reset token",
)
async def reset_password(
    request: Request,
    _rl: Annotated[None, Depends(rate_limit_auth_reset_password)],
    body: ResetPasswordRequest,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    """
    Consume the password-reset token and update the password.
    All existing refresh sessions are revoked for security.

    Raises **400** when the token is invalid or expired.
    Raises **422** when ``new_password`` is too short (< 8 chars).
    """
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for)
    await auth_service.reset_password(body.token, body.new_password)
    log_auth_event("auth.reset_password", outcome="success", client_ip=ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Dev-only debug endpoint (hidden from OpenAPI docs)
# ---------------------------------------------------------------------------

_DEV_ALLOWED_ENVS = frozenset({"local", "docker", "development", "test"})

# Redis key prefixes (must match app/services/email_token_service.py)
_PREFIX_EMAIL_VERIFY = "bf:ev:"
_PREFIX_PASSWORD_RESET = "bf:pr:"


@router.get(
    "/dev/pending-tokens",
    summary="[DEV ONLY] List recent email tokens for testing",
    include_in_schema=False,  # Hidden from OpenAPI / Swagger docs
)
async def dev_pending_tokens(
    settings: SettingsDep,
) -> dict[str, Any]:
    """
    Development helper: returns recent unverified email tokens stored in Redis
    so developers can test email flows without a real email delivery service.

    Only active in non-production environments (local, docker, development, test).
    Returns 404 in staging / production.
    """
    if settings.environment not in _DEV_ALLOWED_ENVS:
        raise HTTPException(status_code=404, detail="Not found")

    from app.core.redis_client import get_redis_client

    redis_client = get_redis_client()
    if redis_client is None:
        return {
            "environment": settings.environment,
            "redis_available": False,
            "tokens": [],
            "note": "Redis is not configured — email tokens cannot be stored or listed.",
        }

    tokens: list[dict[str, Any]] = []

    async def _collect(prefix: str, token_type: str) -> None:
        try:
            keys = await redis_client.keys(f"{prefix}*")
        except Exception:
            return
        for key in keys[:20]:  # cap at 20 per type to avoid huge responses
            token_value = key[len(prefix):]
            try:
                user_id = await redis_client.get(key)
                ttl = await redis_client.ttl(key)
            except Exception:
                user_id = None
                ttl = -1
            tokens.append(
                {
                    "type": token_type,
                    "token": token_value,
                    "user_id": user_id,
                    "ttl_seconds_remaining": ttl,
                    "action_url": (
                        settings.frontend_base_url.rstrip("/")
                        + ("/auth/verify-email" if token_type == "email_verify" else "/auth/reset-password")
                        + f"?token={token_value}"
                    ),
                }
            )

    await _collect(_PREFIX_EMAIL_VERIFY, "email_verify")
    await _collect(_PREFIX_PASSWORD_RESET, "password_reset")

    # Sort by descending TTL so the freshest tokens appear first.
    tokens.sort(key=lambda t: t.get("ttl_seconds_remaining") or 0, reverse=True)

    return {
        "environment": settings.environment,
        "redis_available": True,
        "count": len(tokens),
        "tokens": tokens,
        "note": (
            "Tokens are stored in Redis and consumed on first use. "
            "Copy the action_url into your browser to complete the flow."
        ),
    }
