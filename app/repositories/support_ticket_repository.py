"""CRUD repository for SupportTicket."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_ticket import (
    TICKET_STATUS_OPEN,
    SupportTicket,
)
from app.models.user import User


@dataclass(slots=True)
class TicketFilters:
    status: str | None = None
    priority: str | None = None
    user_id: uuid.UUID | None = None


class SupportTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── user-facing ──────────────────────────────────────────────────────

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        subject: str,
        body: str,
        priority: str = "normal",
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject.strip(),
            body=body.strip(),
            priority=priority,
            status=TICKET_STATUS_OPEN,
        )
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def get_by_id(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        result = await self._session.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[SupportTicket]:
        result = await self._session.execute(
            select(SupportTicket)
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
            .offset(offset)
            .limit(min(limit, 100))
        )
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user_id)
        )
        return int(result.scalar_one() or 0)

    # ── admin ─────────────────────────────────────────────────────────────

    def _where(self, filters: TicketFilters) -> list:
        clauses: list = []
        if filters.status:
            clauses.append(SupportTicket.status == filters.status)
        if filters.priority:
            clauses.append(SupportTicket.priority == filters.priority)
        if filters.user_id:
            clauses.append(SupportTicket.user_id == filters.user_id)
        return clauses

    async def count_all(self, filters: TicketFilters) -> int:
        stmt = select(func.count(SupportTicket.id))
        for c in self._where(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list_all(
        self,
        filters: TicketFilters,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[SupportTicket, str]]:
        """Returns (SupportTicket, user_email) rows, newest first."""
        stmt = (
            select(SupportTicket, User.email)
            .join(User, User.id == SupportTicket.user_id)
            .order_by(SupportTicket.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        for c in self._where(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return [(row[0], str(row[1])) for row in result.all()]

    async def admin_update(
        self,
        ticket: SupportTicket,
        *,
        status: str | None = None,
        admin_note: str | None = None,
        priority: str | None = None,
    ) -> SupportTicket:
        if status:
            ticket.status = status
            if status in ("resolved", "closed") and ticket.resolved_at is None:
                ticket.resolved_at = datetime.now(UTC)
        if admin_note is not None:
            ticket.admin_note = admin_note or None
        if priority:
            ticket.priority = priority
        return ticket

    async def commit(self) -> None:
        await self._session.commit()
