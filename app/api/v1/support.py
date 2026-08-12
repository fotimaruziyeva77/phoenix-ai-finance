"""User-facing support ticket endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SupportTicketRepoDep
from app.schemas.support_tickets import TicketCreate, TicketListResponse, TicketRead

router = APIRouter(prefix="/support", tags=["support"])


@router.post(
    "/tickets",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a support ticket",
)
async def create_ticket(
    body: TicketCreate,
    user: CurrentUser,
    repo: SupportTicketRepoDep,
) -> TicketRead:
    ticket = await repo.create(
        user_id=user.id,
        subject=body.subject,
        body=body.body,
        priority=body.priority,
    )
    await repo.commit()
    refreshed = await repo.get_by_id(ticket.id)
    assert refreshed is not None
    return _to_read(refreshed)


@router.get(
    "/tickets",
    response_model=TicketListResponse,
    summary="List my support tickets",
)
async def list_my_tickets(
    user: CurrentUser,
    repo: SupportTicketRepoDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TicketListResponse:
    total = await repo.count_for_user(user.id)
    items = await repo.list_for_user(user.id, limit=limit, offset=offset)
    return TicketListResponse(
        items=[_to_read(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketRead,
    summary="Get a specific support ticket (owner only)",
)
async def get_ticket(
    ticket_id: UUID,
    user: CurrentUser,
    repo: SupportTicketRepoDep,
) -> TicketRead:
    ticket = await repo.get_by_id(ticket_id)
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return _to_read(ticket)


def _to_read(t) -> TicketRead:
    return TicketRead(
        id=t.id, user_id=t.user_id, subject=t.subject, body=t.body,
        status=t.status, priority=t.priority, admin_note=t.admin_note,
        resolved_at=t.resolved_at, created_at=t.created_at, updated_at=t.updated_at,
    )
