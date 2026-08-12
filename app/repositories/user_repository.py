"""User persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import OAuthProvider, UserRole
from app.models.user import OAuthAccount, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        # Use a SELECT statement rather than session.get() so that:
        # (a) expired objects in the identity map are always reloaded from DB, and
        # (b) selectin-loaded relationships are fetched in the same round-trip.
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_with_oauth(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email)
            .options(selectinload(User.oauth_accounts))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_oauth(
        self,
        provider: OAuthProvider,
        provider_user_id: str,
    ) -> User | None:
        stmt = (
            select(User)
            .join(OAuthAccount, OAuthAccount.user_id == User.id)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
            .options(selectinload(User.oauth_accounts))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_oauth_user(
        self,
        *,
        email: str,
        full_name: str | None,
        provider: OAuthProvider,
        provider_user_id: str,
        provider_email: str | None,
        role: UserRole = UserRole.customer_admin,
    ) -> User:
        user = User(
            email=email,
            password_hash=None,
            full_name=full_name,
            role=role,
            is_verified=True,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise

        oauth = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        self._session.add(oauth)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise

        await self._session.refresh(user)
        return user

    async def link_oauth_account(
        self,
        *,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        provider_email: str | None,
    ) -> OAuthAccount:
        oauth = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        self._session.add(oauth)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(oauth)
        return oauth

    async def update_profile(self, user: User, *, full_name: str | None) -> User:
        user.full_name = full_name
        await self._session.flush()
        return user

    async def delete(self, user: User) -> None:
        """Hard-delete user; CASCADE FKs handle related rows."""
        await self._session.delete(user)
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def create_email_password_user(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str | None,
        role: UserRole = UserRole.customer_admin,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(user)
        return user
