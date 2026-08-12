"""Read-only queries for the audit_log table (superadmin compliance view)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


@dataclass(slots=True)
class AuditLogFilters:
    actor_user_id: uuid.UUID | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    action: str | None = None
    since: datetime | None = None
    until: datetime | None = None


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _where_clauses(self, filters: AuditLogFilters) -> list:
        clauses: list = []
        if filters.actor_user_id is not None:
            clauses.append(AuditLog.actor_user_id == filters.actor_user_id)
        if filters.entity_type is not None:
            clauses.append(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id is not None:
            clauses.append(AuditLog.entity_id == filters.entity_id)
        if filters.action is not None:
            clauses.append(AuditLog.action == filters.action)
        if filters.since is not None:
            clauses.append(AuditLog.created_at >= filters.since)
        if filters.until is not None:
            clauses.append(AuditLog.created_at <= filters.until)
        return clauses

    async def count(self, filters: AuditLogFilters) -> int:
        stmt = select(func.count(AuditLog.id))
        for c in self._where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def list(
        self,
        filters: AuditLogFilters,
        *,
        limit: int,
        offset: int,
    ) -> list[tuple[AuditLog, str | None]]:
        """Returns (AuditLog, actor_email) rows, newest first."""
        stmt = (
            select(AuditLog, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .order_by(AuditLog.created_at.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 200))
        )
        for c in self._where_clauses(filters):
            stmt = stmt.where(c)
        result = await self._session.execute(stmt)
        return [(row[0], str(row[1]) if row[1] else None) for row in result.all()]

    async def distinct_actions(self) -> list[str]:
        """All unique action strings for filter dropdowns."""
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
        result = await self._session.execute(stmt)
        return [str(r[0]) for r in result.all()]

    async def distinct_entity_types(self) -> list[str]:
        """All unique entity_type strings for filter dropdowns."""
        stmt = select(AuditLog.entity_type).distinct().order_by(AuditLog.entity_type)
        result = await self._session.execute(stmt)
        return [str(r[0]) for r in result.all()]
