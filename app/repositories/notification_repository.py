"""Repository for owner dashboard notifications."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.owner_notification import OwnerNotification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        kind: str,
        title: str,
        body: str | None = None,
        reference_id: uuid.UUID | None = None,
        reference_type: str | None = None,
    ) -> OwnerNotification:
        notif = OwnerNotification(
            owner_id=owner_id,
            kind=kind,
            title=title,
            body=body,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        self._session.add(notif)
        return notif

    async def count_unread(self, owner_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OwnerNotification)
            .where(
                OwnerNotification.owner_id == owner_id,
                OwnerNotification.is_read.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_recent(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int = 30,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[OwnerNotification]:
        stmt = (
            select(OwnerNotification)
            .where(OwnerNotification.owner_id == owner_id)
            .order_by(OwnerNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            stmt = stmt.where(OwnerNotification.is_read.is_(False))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, owner_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        stmt = (
            update(OwnerNotification)
            .where(
                OwnerNotification.id == notification_id,
                OwnerNotification.owner_id == owner_id,
            )
            .values(is_read=True)
        )
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def mark_all_read(self, owner_id: uuid.UUID) -> int:
        stmt = (
            update(OwnerNotification)
            .where(
                OwnerNotification.owner_id == owner_id,
                OwnerNotification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount or 0

    async def commit(self) -> None:
        await self._session.commit()
