"""Superadmin webhook delivery log viewer (Feature 14)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import RequireSuperadmin, WebhookLogRepoDep
from app.repositories.webhook_log_repository import WebhookLogFilters

router = APIRouter(prefix="/admin/webhook-logs", tags=["admin-webhook-logs"])


class WebhookLogDto(BaseModel):
    id: uuid.UUID
    source: str
    event_type: str | None
    status: str
    error_message: str | None
    payload_preview: dict | None
    bot_id: uuid.UUID | None
    created_at: datetime
    processed_at: datetime | None


class WebhookLogListResponse(BaseModel):
    items: list[WebhookLogDto]
    total: int
    failed_total: int
    limit: int
    offset: int


def _to_dto(log) -> WebhookLogDto:
    return WebhookLogDto(
        id=log.id,
        source=log.source,
        event_type=log.event_type,
        status=log.status,
        error_message=log.error_message,
        payload_preview=log.payload_preview,
        bot_id=log.bot_id,
        created_at=log.created_at,
        processed_at=log.processed_at,
    )


@router.get(
    "",
    response_model=WebhookLogListResponse,
    summary="List webhook delivery logs (superadmin)",
)
async def list_webhook_logs(
    _admin: RequireSuperadmin,
    repo: WebhookLogRepoDep,
    source: str | None = Query(default=None),
    wh_status: str | None = Query(default=None, alias="status"),
    event_type: str | None = Query(default=None),
    since: str | None = Query(default=None, description="ISO 8601 lower bound, e.g. 2026-01-01T00:00:00Z"),
    until: str | None = Query(default=None, description="ISO 8601 upper bound"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> WebhookLogListResponse:
    def _parse_dt(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid datetime format: {s!r}. Use ISO 8601.",
            )

    filters = WebhookLogFilters(
        source=source,
        status=wh_status,
        event_type=event_type,
        since=_parse_dt(since),
        until=_parse_dt(until),
    )
    total = await repo.count(filters)
    failed_total = await repo.count_failed(filters)
    items = await repo.list(filters, limit=limit, offset=offset)
    return WebhookLogListResponse(
        items=[_to_dto(l) for l in items],
        total=total,
        failed_total=failed_total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{log_id}/retry",
    response_model=WebhookLogDto,
    summary="Mark a failed webhook for retry (superadmin)",
)
async def retry_webhook(
    log_id: uuid.UUID,
    _admin: RequireSuperadmin,
    repo: WebhookLogRepoDep,
) -> WebhookLogDto:
    log = await repo.mark_for_retry(log_id)
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or not in 'failed' status.",
        )
    await repo.commit()
    return _to_dto(log)
