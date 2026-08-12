"""Unauthenticated public endpoints for the embeddable website widget."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import (
    PublicWidgetChatServiceDep,
    WidgetBootstrapServiceDep,
    enforce_public_widget_chat_abuse,
    rate_limit_public_widget_bootstrap,
    rate_limit_public_widget_chat,
)
from app.schemas.public_widget_chat import PublicWidgetChatRequest, PublicWidgetChatResponse
from app.schemas.widget_config import WidgetPublicBootstrapResponse

router = APIRouter(tags=["public-widget"])

RateLimitPublicWidgetChatDep = Annotated[None, Depends(rate_limit_public_widget_chat)]
RateLimitPublicWidgetBootstrapDep = Annotated[None, Depends(rate_limit_public_widget_bootstrap)]
PublicWidgetChatAbuseDep = Annotated[None, Depends(enforce_public_widget_chat_abuse)]


@router.get(
    "/public/widget/{public_widget_key}/bootstrap",
    response_model=WidgetPublicBootstrapResponse,
    summary="Bootstrap embeddable widget (public)",
)
async def get_public_widget_bootstrap(
    public_widget_key: str,
    request: Request,
    _: RateLimitPublicWidgetBootstrapDep,
    bootstrap_service: WidgetBootstrapServiceDep,
) -> WidgetPublicBootstrapResponse:
    return await bootstrap_service.get_bootstrap(
        public_widget_key=public_widget_key,
        origin_header=request.headers.get("origin"),
        referer_header=request.headers.get("referer"),
    )


@router.post(
    "/public/widget/{public_widget_key}/chat",
    response_model=PublicWidgetChatResponse,
    summary="Send a visitor message (public widget)",
    description=(
        "REST-first public chat: validates widget key, domain allowlist, and visitor session; "
        "runs the same AI path as owner test chat on a ``web_widget`` conversation."
    ),
)
async def post_public_widget_chat(
    public_widget_key: str,
    request: Request,
    _: RateLimitPublicWidgetChatDep,
    body: PublicWidgetChatRequest,
    __: PublicWidgetChatAbuseDep,
    chat_service: PublicWidgetChatServiceDep,
) -> PublicWidgetChatResponse:
    return await chat_service.send_public_message(
        public_widget_key=public_widget_key,
        origin_header=request.headers.get("origin"),
        referer_header=request.headers.get("referer"),
        body=body,
    )
