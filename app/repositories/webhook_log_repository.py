"""Webhook log CRUD (Feature 14)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_log import WebhookLog


@dataclass(slots=True)
class WebhookLogFilters:
    source: str | None = None
    status: str | None = None
    event_type: str | None = None
    since: Optional[datetime] = field(default=None)
    until: Optional[datetime] = field(default=None)


class WebhookLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        source: str,
        event_type: str | None = None,
        status: str = "received",
        error_message: str | None = None,
        payload_preview: dict | None = None,
        bot_id: uuid.UUID | None = None,
        processed_at: datetime | None = None,
    ) -> WebhookLog:
        log = WebhookLog(
            source=source,
            event_type=event_type,
            status=status,
            error_message=error_message,
            payload_preview=payload_preview,
            bot_id=bot_id,
            processed_at=processed_at,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def count(self, filters: WebhookLogFilters) -> int:
        stmt = select(func.count(WebhookLog.id))
        stmt = self._apply_filters(stmt, filters)
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_failed(self, filters: WebhookLogFilters) -> int:
        """Count failed webhooks matching the same source/date filters (ignores status filter)."""
        failed_filters = WebhookLogFilters(
            source=filters.source,
            status="failed",
            event_type=filters.event_type,
            since=filters.since,
            until=filters.until,
        )
        return await self.count(failed_filters)

    async def list(
        self,
        filters: WebhookLogFilters,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WebhookLog]:
        stmt = (
            select(WebhookLog)
            .order_by(WebhookLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        stmt = self._apply_filters(stmt, filters)
        return list((await self._session.execute(stmt)).scalars())

    @staticmethod
    def _apply_filters(stmt, filters: WebhookLogFilters):
        if filters.source:
            stmt = stmt.where(WebhookLog.source == filters.source)
        if filters.status:
            stmt = stmt.where(WebhookLog.status == filters.status)
        if filters.event_type:
            stmt = stmt.where(WebhookLog.event_type == filters.event_type)
        if filters.since:
            stmt = stmt.where(WebhookLog.created_at >= filters.since)
        if filters.until:
            stmt = stmt.where(WebhookLog.created_at <= filters.until)
        return stmt

    async def mark_for_retry(self, log_id: uuid.UUID) -> WebhookLog | None:
        """Reset a failed webhook to 'received' so it can be re-processed."""
        stmt = select(WebhookLog).where(WebhookLog.id == log_id)
        result = await self._session.execute(stmt)
        log = result.scalar_one_or_none()
        if log is None or log.status != "failed":
            return None
        log.status = "received"
        log.error_message = None
        log.processed_at = None
        await self._session.flush()
        return log

    async def commit(self) -> None:
        await self._session.commit()
