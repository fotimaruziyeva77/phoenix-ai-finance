"""Owner-scoped CRM leads API (dashboard)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, LeadPipelineServiceDep
from app.repositories.lead_repository import LeadListFilters
from app.schemas.lead import (
    LeadEventListResponse,
    LeadListResponse,
    LeadPipelinePatch,
    LeadRead,
    LeadStatusLiteral,
    LeadStatusPatchBody,
    LeadTemperatureLiteral,
)

router = APIRouter(tags=["leads"])


@router.get(
    "/leads",
    response_model=LeadListResponse,
    summary="List leads in the current workspace",
)
async def list_leads(
    user: CurrentUser,
    lead_pipeline: LeadPipelineServiceDep,
    status: LeadStatusLiteral | None = Query(
        default=None,
        description="Filter by pipeline status.",
    ),
    niche: str | None = Query(
        default=None,
        max_length=120,
        description="Filter by niche id (matches ``Lead.niche_id``).",
    ),
    temperature: LeadTemperatureLiteral | None = Query(
        default=None,
        description="Filter by lead temperature.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    after: str | None = Query(
        default=None,
        description=(
            "Opaque cursor for cursor-based pagination (from ``next_cursor`` in a previous "
            "response). When provided, ``offset`` is ignored and results are ordered by "
            "``created_at DESC, id DESC``."
        ),
    ),
) -> LeadListResponse:
    filters = LeadListFilters(
        status=status,
        niche_id=niche,
        lead_temperature=temperature,
    )
    if after is not None:
        return await lead_pipeline.list_leads_for_owner_cursor(
            user,
            filters=filters,
            limit=limit,
            after_cursor=after,
        )
    return await lead_pipeline.list_leads_for_owner(
        user,
        filters=filters,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/leads/{lead_id}",
    response_model=LeadRead,
    summary="Get one lead for the current workspace",
)
async def get_lead(
    lead_id: UUID,
    user: CurrentUser,
    lead_pipeline: LeadPipelineServiceDep,
) -> LeadRead:
    return await lead_pipeline.get_lead_detail_for_owner(user, lead_id)


@router.get(
    "/leads/{lead_id}/events",
    response_model=LeadEventListResponse,
    summary="CRM activity timeline (append-only events for this lead)",
)
async def list_lead_timeline(
    lead_id: UUID,
    user: CurrentUser,
    lead_pipeline: LeadPipelineServiceDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> LeadEventListResponse:
    return await lead_pipeline.list_lead_timeline_for_owner(
        user,
        lead_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/leads/{lead_id}/status",
    response_model=LeadRead,
    summary="Update lead pipeline status (and optional temperature or notes)",
)
async def patch_lead_status(
    lead_id: UUID,
    body: LeadStatusPatchBody,
    user: CurrentUser,
    lead_pipeline: LeadPipelineServiceDep,
) -> LeadRead:
    patch = LeadPipelinePatch.model_validate(body.model_dump(exclude_unset=True))
    return await lead_pipeline.update_lead_pipeline(user, lead_id, patch)
