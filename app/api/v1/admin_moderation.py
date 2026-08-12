"""Superadmin moderation: suspend/activate users and bots (audited)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminModerationServiceDep, RequireSuperadmin
from app.schemas.admin_moderation import AdminModerationReasonBody
from app.schemas.platform_admin import AdminBotDetail, AdminUserDetail

router = APIRouter(prefix="/admin", tags=["admin-moderation"])


@router.post(
    "/users/{user_id}/suspend",
    response_model=AdminUserDetail,
    summary="Suspend user (superadmin)",
)
async def admin_suspend_user(
    user_id: UUID,
    _admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
    body: AdminModerationReasonBody | None = None,
) -> AdminUserDetail:
    payload = body or AdminModerationReasonBody()
    row = await svc.suspend_user(
        actor_user_id=_admin.id,
        user_id=user_id,
        reason=payload.reason,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return row


@router.post(
    "/users/{user_id}/activate",
    response_model=AdminUserDetail,
    summary="Activate user (superadmin)",
)
async def admin_activate_user(
    user_id: UUID,
    _admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
) -> AdminUserDetail:
    row = await svc.activate_user(actor_user_id=_admin.id, user_id=user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return row


@router.post(
    "/bots/{bot_id}/suspend",
    response_model=AdminBotDetail,
    summary="Platform-suspend bot (superadmin)",
)
async def admin_suspend_bot(
    bot_id: UUID,
    _admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
    body: AdminModerationReasonBody | None = None,
) -> AdminBotDetail:
    payload = body or AdminModerationReasonBody()
    row = await svc.suspend_bot(
        actor_user_id=_admin.id,
        bot_id=bot_id,
        reason=payload.reason,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    return row


@router.post(
    "/bots/{bot_id}/activate",
    response_model=AdminBotDetail,
    summary="Clear platform suspension on bot (superadmin)",
)
async def admin_activate_bot(
    bot_id: UUID,
    _admin: RequireSuperadmin,
    svc: AdminModerationServiceDep,
) -> AdminBotDetail:
    row = await svc.activate_bot(actor_user_id=_admin.id, bot_id=bot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    return row
