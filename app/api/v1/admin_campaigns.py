"""Superadmin email campaign management (Feature 11)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DbSession, EmailCampaignRepoDep, RequireSuperadmin, SettingsDep
from app.integrations.email.resend_client import ResendEmailClient
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin/campaigns", tags=["admin-campaigns"])

VALID_SEGMENTS = ("all_users", "past_due", "free_plan", "paid_users", "inactive_7d")


# ── Schemas ───────────────────────────────────────────────────────────────

class CampaignRead(BaseModel):
    id: uuid.UUID
    subject: str
    body_html: str
    target_segment: str
    status: str
    estimated_recipients: int | None
    sent_count: int
    failed_count: int
    created_by_id: uuid.UUID | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    items: list[CampaignRead]
    total: int
    limit: int
    offset: int


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(..., min_length=3, max_length=256)
    body_html: str = Field(..., min_length=10)
    target_segment: str = Field(..., pattern="^(all_users|past_due|free_plan|paid_users|inactive_7d)$")


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str | None = Field(default=None, min_length=3, max_length=256)
    body_html: str | None = Field(default=None, min_length=10)
    target_segment: str | None = Field(
        default=None,
        pattern="^(all_users|past_due|free_plan|paid_users|inactive_7d)$",
    )


def _to_read(c) -> CampaignRead:
    return CampaignRead(
        id=c.id, subject=c.subject, body_html=c.body_html,
        target_segment=c.target_segment, status=c.status,
        estimated_recipients=c.estimated_recipients,
        sent_count=c.sent_count, failed_count=c.failed_count,
        created_by_id=c.created_by_id,
        sent_at=c.sent_at, created_at=c.created_at, updated_at=c.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("", response_model=CampaignListResponse, summary="List campaigns (superadmin)")
async def list_campaigns(
    _admin: RequireSuperadmin,
    repo: EmailCampaignRepoDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> CampaignListResponse:
    total = await repo.count_all()
    items = await repo.list_all(limit=limit, offset=offset)
    return CampaignListResponse(
        items=[_to_read(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft campaign (superadmin)",
)
async def create_campaign(
    body: CampaignCreate,
    admin: RequireSuperadmin,
    repo: EmailCampaignRepoDep,
    session: DbSession,
) -> CampaignRead:
    recipients = await repo.get_recipients(body.target_segment)
    campaign = await repo.create(
        subject=body.subject,
        body_html=body.body_html,
        target_segment=body.target_segment,
        created_by_id=admin.id,
    )
    await repo.update_status(campaign, status="draft", estimated_recipients=len(recipients))

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="campaign_created",
        entity_type="campaign",
        entity_id=campaign.id,
        after_snapshot={
            "subject": body.subject,
            "target_segment": body.target_segment,
            "estimated_recipients": len(recipients),
        },
    )
    await repo.commit()
    refreshed = await repo.get_by_id(campaign.id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Campaign disappeared after create.")
    return _to_read(refreshed)


@router.patch(
    "/{campaign_id}",
    response_model=CampaignRead,
    summary="Edit a draft campaign subject/body/segment (superadmin)",
)
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    admin: RequireSuperadmin,
    repo: EmailCampaignRepoDep,
    session: DbSession,
) -> CampaignRead:
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or failed campaigns can be edited.",
        )

    before = {"subject": campaign.subject, "body_html": campaign.body_html, "target_segment": campaign.target_segment}

    if body.subject is not None:
        campaign.subject = body.subject
    if body.body_html is not None:
        campaign.body_html = body.body_html
    if body.target_segment is not None:
        campaign.target_segment = body.target_segment
        # Re-estimate recipients for new segment
        recipients = await repo.get_recipients(body.target_segment)
        campaign.estimated_recipients = len(recipients)
    campaign.updated_at = datetime.now(UTC)

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="campaign_updated",
        entity_type="campaign",
        entity_id=campaign_id,
        before_snapshot=before,
        after_snapshot={"subject": campaign.subject, "target_segment": campaign.target_segment},
    )
    await repo.commit()
    refreshed = await repo.get_by_id(campaign_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Campaign disappeared after update.")
    return _to_read(refreshed)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a draft campaign (superadmin)",
)
async def delete_campaign(
    campaign_id: uuid.UUID,
    admin: RequireSuperadmin,
    repo: EmailCampaignRepoDep,
    session: DbSession,
) -> None:
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft or failed campaigns can be deleted.",
        )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="campaign_deleted",
        entity_type="campaign",
        entity_id=campaign_id,
        before_snapshot={"subject": campaign.subject, "target_segment": campaign.target_segment},
    )
    await repo.delete(campaign)
    await repo.commit()


@router.post(
    "/{campaign_id}/send",
    response_model=CampaignRead,
    summary="Send a campaign to all segment recipients (superadmin)",
)
async def send_campaign(
    campaign_id: uuid.UUID,
    admin: RequireSuperadmin,
    repo: EmailCampaignRepoDep,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    session: DbSession,
) -> CampaignRead:
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign already sent or currently sending.",
        )

    recipients = await repo.get_recipients(campaign.target_segment)
    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recipients found for this segment.",
        )

    # Check email is configured BEFORE setting status to "sending"
    client = ResendEmailClient(settings)
    if not client.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sending is not configured (RESEND_API_KEY missing). Cannot send campaign.",
        )

    await repo.update_status(
        campaign, status="sending",
        estimated_recipients=len(recipients),
    )

    audit = AuditService(session)
    await audit.log_entity_event(
        actor_user_id=admin.id,
        action="campaign_sent",
        entity_type="campaign",
        entity_id=campaign_id,
        metadata_json={
            "target_segment": campaign.target_segment,
            "estimated_recipients": len(recipients),
        },
    )
    await repo.commit()

    # Fire-and-forget background send
    background_tasks.add_task(
        _send_campaign_emails,
        campaign_id=campaign.id,
        subject=campaign.subject,
        body_html=campaign.body_html,
        recipients=recipients,
        settings=settings,
    )

    refreshed = await repo.get_by_id(campaign_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Campaign disappeared after send.")
    return _to_read(refreshed)


async def _send_campaign_emails(
    *,
    campaign_id: uuid.UUID,
    subject: str,
    body_html: str,
    recipients,
    settings,
) -> None:
    """Background task: send emails and update campaign stats."""
    from app.core.db import get_session_maker
    from app.repositories.email_campaign_repository import EmailCampaignRepository

    async_session_factory = get_session_maker()

    sent = 0
    failed = 0

    client = ResendEmailClient(settings)
    # Email is guaranteed enabled here (checked in send_campaign before enqueueing)
    for r in recipients:
        personal_html = body_html.replace("{{name}}", r.full_name or r.email)
        ok = await client.send(
            to=r.email,
            subject=subject,
            html=personal_html,
        )
        if ok:
            sent += 1
        else:
            failed += 1

    # Update campaign record — best-effort, never crash
    try:
        async with async_session_factory() as session:  # type: ignore[attr-defined]
            repo = EmailCampaignRepository(session)
            campaign = await repo.get_by_id(campaign_id)
            if campaign:
                final_status = "sent" if sent > 0 else "failed"
                await repo.update_status(
                    campaign,
                    status=final_status,
                    sent_count=sent,
                    failed_count=failed,
                    sent_at=datetime.now(UTC),
                )
                await repo.commit()
    except Exception:  # noqa: BLE001
        pass
