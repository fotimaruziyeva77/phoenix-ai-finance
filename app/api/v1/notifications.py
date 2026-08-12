"""Owner dashboard notifications API (bell icon)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.repositories.notification_repository import NotificationRepository
from app.services.owner_notification_service import OwnerNotificationService

router = APIRouter(tags=["notifications"])


class NotificationItem(BaseModel):
    id: str
    kind: str
    title: str
    body: str | None
    reference_id: str | None
    reference_type: str | None
    is_read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool


class MarkAllReadResponse(BaseModel):
    marked_count: int


def _to_item(n: object) -> NotificationItem:
    return NotificationItem(
        id=str(n.id),
        kind=n.kind,
        title=n.title,
        body=n.body,
        reference_id=str(n.reference_id) if n.reference_id else None,
        reference_type=n.reference_type,
        is_read=n.is_read,
        created_at=n.created_at.isoformat(),
    )


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List recent notifications for the current user",
)
async def list_notifications(
    user: CurrentUser,
    session: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    svc = OwnerNotificationService(NotificationRepository(session))
    items = await svc.list_recent(
        user.id, limit=limit, offset=offset, unread_only=unread_only
    )
    count = await svc.count_unread(user.id)
    return NotificationListResponse(
        items=[_to_item(n) for n in items],
        unread_count=count,
    )


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count (for badge)",
)
async def unread_count(
    user: CurrentUser,
    session: DbSession,
) -> UnreadCountResponse:
    svc = OwnerNotificationService(NotificationRepository(session))
    count = await svc.count_unread(user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark a single notification as read",
)
async def mark_read(
    notification_id: UUID,
    user: CurrentUser,
    session: DbSession,
) -> MarkReadResponse:
    svc = OwnerNotificationService(NotificationRepository(session))
    ok = await svc.mark_read(user.id, notification_id)
    await NotificationRepository(session).commit()
    return MarkReadResponse(success=ok)


@router.patch(
    "/notifications/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    user: CurrentUser,
    session: DbSession,
) -> MarkAllReadResponse:
    svc = OwnerNotificationService(NotificationRepository(session))
    count = await svc.mark_all_read(user.id)
    await NotificationRepository(session).commit()
    return MarkAllReadResponse(marked_count=count)
