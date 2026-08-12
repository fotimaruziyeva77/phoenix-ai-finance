"""Persistence for :class:`~app.models.refresh_session.RefreshSession`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_session import RefreshSession


class RefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_jti(self, jti: str) -> RefreshSession | None:
        stmt = select(RefreshSession).where(RefreshSession.jti == jti)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_session(self, row: RefreshSession) -> RefreshSession:
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def revoke_session(
        self,
        session_id: uuid.UUID,
        *,
        revoked_at: datetime,
        reason: str,
    ) -> None:
        await self._session.execute(
            update(RefreshSession)
            .where(RefreshSession.id == session_id)
            .values(revoked_at=revoked_at, revoke_reason=reason, updated_at=revoked_at),
        )

    async def revoke_all_active_for_user(
        self,
        user_id: uuid.UUID,
        *,
        revoked_at: datetime,
        reason: str,
        except_session_id: uuid.UUID | None = None,
    ) -> None:
        now = revoked_at
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > now,
            )
            .values(revoked_at=revoked_at, revoke_reason=reason, updated_at=revoked_at)
        )
        if except_session_id is not None:
            stmt = stmt.where(RefreshSession.id != except_session_id)
        await self._session.execute(stmt)

    async def revoke_family_active_sessions(
        self,
        family_id: uuid.UUID,
        *,
        revoked_at: datetime,
        reason: str,
    ) -> None:
        await self._session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at, revoke_reason=reason, updated_at=revoked_at),
        )

    async def list_active_sessions_for_user(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> list[RefreshSession]:
        t = now or datetime.now(UTC)
        stmt = (
            select(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > t,
            )
            .order_by(RefreshSession.issued_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
