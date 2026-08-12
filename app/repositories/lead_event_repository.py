"""Insert and list :class:`~app.models.lead_event.LeadEvent` rows (append-only)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.lead_event import LeadEvent


class LeadEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def insert_event(
        self,
        *,
        lead_id: uuid.UUID,
        event_type: str,
        actor_type: str,
        actor_id: uuid.UUID | None,
        old_value: str | None,
        new_value: str | None,
        metadata: Mapping[str, object] | None,
    ) -> LeadEvent:
        if event_type not in LeadEvent.EVENT_TYPES:
            raise ValueError(f"unsupported lead event_type: {event_type!r}")
        if actor_type not in LeadEvent.ACTOR_TYPES:
            raise ValueError(f"unsupported actor_type: {actor_type!r}")
        meta_dict = dict(metadata) if metadata is not None else None
        row = LeadEvent(
            lead_id=lead_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            old_value=old_value,
            new_value=new_value,
            metadata_json=meta_dict,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    def _owned_timeline_stmt(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> Select[tuple[LeadEvent]]:
        return (
            select(LeadEvent)
            .join(Lead, Lead.id == LeadEvent.lead_id)
            .where(Lead.id == lead_id, Lead.owner_id == owner_id)
            .order_by(LeadEvent.created_at.asc(), LeadEvent.id.asc())
        )

    async def list_events_for_lead_owned(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeadEvent]:
        stmt = (
            self._owned_timeline_stmt(owner_id=owner_id, lead_id=lead_id)
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 500))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_events_for_lead_owned(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> int:
        stmt = (
            select(func.count(LeadEvent.id))
            .select_from(LeadEvent)
            .join(Lead, Lead.id == LeadEvent.lead_id)
            .where(Lead.id == lead_id, Lead.owner_id == owner_id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)
