"""
Bots workspace API (owner-scoped CRUD).

All handlers scope data to ``user.id`` as owner. ``UserRole.superadmin`` does **not** expand this
scope; platform-wide bot listing belongs under ``/api/v1/admin/...`` with explicit RBAC.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import BillingServiceDep, BotServiceDep, CurrentUser
from app.schemas.bots import BotCreate, BotListResponse, BotRead, BotUpdate

router = APIRouter(tags=["bots"])


@router.get(
    "/bots",
    response_model=BotListResponse,
    summary="List bots in the current workspace",
)
async def list_bots(
    user: CurrentUser,
    bot_service: BotServiceDep,
) -> BotListResponse:
    items = await bot_service.list_bots_for_user(user)
    return BotListResponse(items=items)


@router.post(
    "/bots",
    response_model=BotRead,
    status_code=201,
    summary="Create bot for current user",
)
async def create_bot(
    payload: BotCreate,
    user: CurrentUser,
    bot_service: BotServiceDep,
    billing_service: BillingServiceDep,
) -> BotRead:
    # Serialize per-owner so the count→limit→insert below is race-free (prevents exceeding
    # bots_max via concurrent requests), then enforce the plan bot limit before creating.
    await bot_service.acquire_owner_create_lock(user.id)
    current_bots = await bot_service.list_bots_for_user(user)
    await billing_service.enforce_bot_limit(user, len(current_bots))
    return await bot_service.create_bot_for_user(user, payload)


@router.get(
    "/bots/{bot_id}",
    response_model=BotRead,
    summary="Get one bot for current user",
)
async def get_bot(
    bot_id: UUID,
    user: CurrentUser,
    bot_service: BotServiceDep,
) -> BotRead:
    return await bot_service.get_bot_for_user(user, bot_id)


@router.patch(
    "/bots/{bot_id}",
    response_model=BotRead,
    summary="Update one bot for current user",
)
async def update_bot(
    bot_id: UUID,
    payload: BotUpdate,
    user: CurrentUser,
    bot_service: BotServiceDep,
) -> BotRead:
    return await bot_service.update_bot_for_user(user, bot_id, payload)


@router.delete(
    "/bots/{bot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete one bot for current user",
)
async def delete_bot(
    bot_id: UUID,
    user: CurrentUser,
    bot_service: BotServiceDep,
) -> None:
    await bot_service.delete_bot_for_user(user, bot_id)


@router.post(
    "/bots/{bot_id}/archive",
    response_model=BotRead,
    summary="Archive one bot for current user",
)
async def archive_bot(
    bot_id: UUID,
    user: CurrentUser,
    bot_service: BotServiceDep,
) -> BotRead:
    return await bot_service.archive_bot_for_user(user, bot_id)


@router.post(
    "/bots/{bot_id}/clone",
    response_model=BotRead,
    status_code=201,
    summary="Duplicate a bot (creates a draft copy)",
)
async def clone_bot(
    bot_id: UUID,
    user: CurrentUser,
    bot_service: BotServiceDep,
    billing_service: BillingServiceDep,
) -> BotRead:
    await bot_service.acquire_owner_create_lock(user.id)
    current_bots = await bot_service.list_bots_for_user(user)
    await billing_service.enforce_bot_limit(user, len(current_bots))
    return await bot_service.clone_bot_for_user(user, bot_id)
