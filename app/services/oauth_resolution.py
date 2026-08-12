"""Shared user resolution for OAuth providers (by provider id, email link, create)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.models.enums import OAuthProvider
from app.models.user import User
from app.schemas.auth import AuthSessionResponse
from app.services.auth_exceptions import AuthServiceError, InactiveUserError
from app.services.auth_service import AuthService


async def resolve_oauth_login(
    auth_service: AuthService,
    *,
    provider: OAuthProvider,
    provider_user_id: str,
    email: str,
    full_name: str | None,
    link_conflict_error: type[AuthServiceError],
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthSessionResponse:
    """
    Find or create user for an OAuth identity and issue a new refresh session (new family).

    ``link_conflict_error`` is raised (409) when the email account is already
    bound to another identity for the same provider.
    """
    repo = auth_service.user_repository
    user = await repo.get_user_by_oauth(provider, provider_user_id)
    if user is not None:
        if not user.is_active:
            raise InactiveUserError()
        return await auth_service.create_session_for_user(
            user,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    existing = await repo.get_by_email_with_oauth(email)
    if existing is not None:
        return await _link_oauth_to_existing_user(
            auth_service,
            existing=existing,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            link_conflict_error=link_conflict_error,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    try:
        user = await repo.create_oauth_user(
            email=email,
            full_name=full_name,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
        )
    except IntegrityError:
        return await resolve_oauth_login(
            auth_service,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            full_name=full_name,
            link_conflict_error=link_conflict_error,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    return await auth_service.create_session_for_user(
        user,
        client_ip=client_ip,
        user_agent=user_agent,
    )


async def _link_oauth_to_existing_user(
    auth_service: AuthService,
    *,
    existing: User,
    provider: OAuthProvider,
    provider_user_id: str,
    email: str,
    link_conflict_error: type[AuthServiceError],
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthSessionResponse:
    repo = auth_service.user_repository
    for acc in existing.oauth_accounts:
        if acc.provider == provider and acc.provider_user_id != provider_user_id:
            raise link_conflict_error(
                "This email is already linked to a different account for this provider"
            )

    target: User = existing
    has_same = any(
        a.provider == provider and a.provider_user_id == provider_user_id
        for a in existing.oauth_accounts
    )
    if not has_same:
        try:
            await repo.link_oauth_account(
                user_id=existing.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
            )
        except IntegrityError:
            other = await repo.get_user_by_oauth(provider, provider_user_id)
            if other is None:
                raise link_conflict_error() from None
            target = other

    if not target.is_active:
        raise InactiveUserError()

    return await auth_service.create_session_for_user(
        target,
        client_ip=client_ip,
        user_agent=user_agent,
    )
