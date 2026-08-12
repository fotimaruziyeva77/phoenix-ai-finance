"""Superadmin support ticket management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, RequireSuperadmin, SupportTicketRepoDep
from app.models.user import User
from app.repositories.support_ticket_repository import TicketFilters
from app.schemas.support_tickets import AdminTicketListResponse, AdminTicketRead, AdminTicketUpdate

router = APIRouter(prefix="/admin/support", tags=["admin-support"])


async def _ticket_read(ticket, session) -> AdminTicketRead:
    """Build AdminTicketRead with resolved user_email."""
    email_row = await session.execute(
        select(User.email).where(User.id == ticket.user_id)
    )
    user_email = email_row.scalar_one_or_none() or ""
    return AdminTicketRead(
        id=ticket.id, user_id=ticket.user_id, user_email=user_email,
        subject=ticket.subject, body=ticket.body, status=ticket.status,
        priority=ticket.priority, admin_note=ticket.admin_note,
        resolved_at=ticket.resolved_at,
        created_at=ticket.created_at, updated_at=ticket.updated_at,
    )


@router.get(
    "/tickets",
    response_model=AdminTicketListResponse,
    summary="List all support tickets (superadmin)",
)
async def admin_list_tickets(
    _admin: RequireSuperadmin,
    repo: SupportTicketRepoDep,
    ticket_status: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminTicketListResponse:
    filters = TicketFilters(status=ticket_status, priority=priority)
    total = await repo.count_all(filters)
    rows  = await repo.list_all(filters, limit=limit, offset=offset)
    items = [
        AdminTicketRead(
            id=t.id, user_id=t.user_id, user_email=email,
            subject=t.subject, body=t.body, status=t.status,
            priority=t.priority, admin_note=t.admin_note,
            resolved_at=t.resolved_at,
            created_at=t.created_at, updated_at=t.updated_at,
        )
        for t, email in rows
    ]
    return AdminTicketListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch(
    "/tickets/{ticket_id}",
    response_model=AdminTicketRead,
    summary="Update ticket status / add admin note (superadmin)",
)
async def admin_update_ticket(
    ticket_id: UUID,
    body: AdminTicketUpdate,
    _admin: RequireSuperadmin,
    repo: SupportTicketRepoDep,
    session: DbSession,
) -> AdminTicketRead:
    ticket = await repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    await repo.admin_update(
        ticket,
        status=body.status,
        admin_note=body.admin_note,
        priority=body.priority,
    )
    await repo.commit()
    refreshed = await repo.get_by_id(ticket_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ticket disappeared after update.")
    return await _ticket_read(refreshed, session)
