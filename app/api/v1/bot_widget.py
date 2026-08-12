"""Owner-scoped embed widget configuration (dashboard)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, WidgetConfigServiceDep
from app.schemas.widget_config import (
    BotWidgetConfigResponse,
    WidgetConfigUpdate,
    bot_widget_config_response_from_read,
)

router = APIRouter(tags=["bots"])


@router.get(
    "/bots/{bot_id}/widget",
    response_model=BotWidgetConfigResponse,
    summary="Get or create widget configuration for a bot",
)
async def get_bot_widget(
    bot_id: UUID,
    user: CurrentUser,
    widget_service: WidgetConfigServiceDep,
) -> BotWidgetConfigResponse:
    read = await widget_service.get_or_create_widget_config_for_bot(user, bot_id)
    return bot_widget_config_response_from_read(read)


@router.patch(
    "/bots/{bot_id}/widget",
    response_model=BotWidgetConfigResponse,
    summary="Update widget configuration for a bot",
)
async def patch_bot_widget(
    bot_id: UUID,
    payload: WidgetConfigUpdate,
    user: CurrentUser,
    widget_service: WidgetConfigServiceDep,
) -> BotWidgetConfigResponse:
    await widget_service.get_or_create_widget_config_for_bot(user, bot_id)
    read = await widget_service.update_widget_config_for_bot(user, bot_id, payload)
    return bot_widget_config_response_from_read(read)
