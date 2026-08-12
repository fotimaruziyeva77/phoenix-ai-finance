"""Owner-scoped persistence for :class:`~app.models.lead.Lead`."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import base64

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import LEAD_OPEN_PIPELINE_STATUSES, Lead


# ── Cursor helpers ────────────────────────────────────────────────────────────

def encode_lead_cursor(created_at: datetime, lead_id: uuid.UUID) -> str:
    """Encode (created_at, id) pair as a URL-safe base64 cursor string."""
    payload = f"{created_at.isoformat()}|{lead_id}"
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_lead_cursor(cursor: str) -> tuple[datetime, uuid.UUID] | None:
    """Decode cursor; returns None on malformed input."""
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_part, id_part = payload.split("|", 1)
        return datetime.fromisoformat(ts_part), uuid.UUID(id_part)
    except Exception:
        return None


@dataclass(slots=True)
class LeadListFilters:
    """Optional narrowing for owner-scoped lead lists (CRM inbox / per-bot views)."""

    status: str | None = None
    bot_id: uuid.UUID | None = None
    niche_id: str | None = None
    lead_temperature: str | None = None


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def get_lead_by_conversation_id(self, conversation_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.conversation_id == conversation_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_lead_by_id_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.owner_id == owner_id).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leads_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        from sqlalchemy.orm import selectinload

        stmt = (
            self._build_owner_list_stmt(owner_id=owner_id, filters=filters)
            .options(selectinload(Lead.bot), selectinload(Lead.events))
            .order_by(Lead.updated_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_leads_for_owner_cursor(
        self,
        *,
        owner_id: uuid.UUID,
        filters: "LeadListFilters | None" = None,
        limit: int = 50,
        after_created_at: datetime | None = None,
        after_id: uuid.UUID | None = None,
    ) -> list[Lead]:
        """
        Cursor-based listing ordered by ``created_at DESC, id DESC``.

        When ``after_created_at`` + ``after_id`` are given, returns only rows
        that come *after* that position in the sort order (exclusive).
        Fetch ``limit + 1`` rows so callers can detect ``has_more``.
        """
        stmt = (
            self._build_owner_list_stmt(owner_id=owner_id, filters=filters)
            .order_by(Lead.created_at.desc(), Lead.id.desc())
            .limit(min(max(limit, 1), 200) + 1)
        )
        if after_created_at is not None and after_id is not None:
            stmt = stmt.where(
                or_(
                    Lead.created_at < after_created_at,
                    and_(Lead.created_at == after_created_at, Lead.id < after_id),
                )
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_leads_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None = None,
    ) -> int:
        stmt = self._build_owner_list_stmt(owner_id=owner_id, filters=filters).with_only_columns(
            func.count(Lead.id)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def update_lead_pipeline_fields(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
        status: str | None = None,
        lead_temperature: str | None = None,
        notes: str | None = None,
        assignee_user_id: uuid.UUID | None = None,
        touch_status: bool = False,
        touch_temperature: bool = False,
        touch_notes: bool = False,
        touch_assignee: bool = False,
    ) -> Lead | None:
        lead = await self.get_lead_by_id_for_owner(owner_id=owner_id, lead_id=lead_id)
        if lead is None:
            return None
        if touch_status and status is not None:
            lead.status = status
        if touch_temperature:
            lead.lead_temperature = lead_temperature
        if touch_notes:
            lead.notes = notes
        if touch_assignee:
            lead.assignee_user_id = assignee_user_id
        await self._session.flush()
        await self._session.refresh(lead)
        return lead

    def _build_owner_list_stmt(
        self,
        *,
        owner_id: uuid.UUID,
        filters: LeadListFilters | None,
    ) -> Select[tuple[Lead]]:
        stmt = select(Lead).where(Lead.owner_id == owner_id)
        active = filters or LeadListFilters()
        if active.status is not None:
            stmt = stmt.where(Lead.status == active.status)
        if active.bot_id is not None:
            stmt = stmt.where(Lead.bot_id == active.bot_id)
        if active.niche_id is not None:
            stmt = stmt.where(Lead.niche_id == active.niche_id)
        if active.lead_temperature is not None:
            stmt = stmt.where(Lead.lead_temperature == active.lead_temperature)
        return stmt

    async def create_lead(
        self,
        *,
        bot_id: uuid.UUID,
        owner_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        niche_id: str,
        lead_score: int | None,
        lead_temperature: str | None,
        summary: str | None,
        source_channel: str | None,
        collected_data_json: Mapping[str, object] | None,
        phone: str | None,
        name: str | None = None,
        status: str = "new",
    ) -> Lead:
        row = Lead(
            bot_id=bot_id,
            owner_id=owner_id,
            conversation_id=conversation_id,
            niche_id=niche_id,
            lead_score=lead_score,
            lead_temperature=lead_temperature,
            summary=summary,
            source_channel=source_channel,
            collected_data_json=dict(collected_data_json) if collected_data_json is not None else None,
            phone=phone,
            name=name,
            status=status,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def find_open_lead_same_normalized_phone(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        phone_digits: str,
    ) -> Lead | None:
        """
        Same owner + bot + **digits-only** phone match while the existing row is in an open pipeline stage.

        Uses PostgreSQL ``regexp_replace`` to normalize stored ``phone`` values (portable unit tests stub this).
        """
        if not phone_digits:
            return None
        normalized = func.regexp_replace(func.coalesce(Lead.phone, ""), r"[^0-9]", "", "g")
        stmt = (
            select(Lead)
            .where(
                Lead.owner_id == owner_id,
                Lead.bot_id == bot_id,
                Lead.status.in_(LEAD_OPEN_PIPELINE_STATUSES),
                normalized == phone_digits,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_leads_same_phone_recent(
        self,
        *,
        owner_id: uuid.UUID,
        bot_id: uuid.UUID,
        phone_digits: str,
        hours: int = 24,
    ) -> int:
        """Count leads (any status) with the same normalized phone in the rolling window."""
        if not phone_digits:
            return 0
        since = datetime.now(UTC) - timedelta(hours=hours)
        normalized = func.regexp_replace(func.coalesce(Lead.phone, ""), r"[^0-9]", "", "g")
        stmt = select(func.count(Lead.id)).where(
            Lead.owner_id == owner_id,
            Lead.bot_id == bot_id,
            normalized == phone_digits,
            Lead.created_at >= since,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)
