"""Email campaign CRUD + recipient querying (Feature 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_campaign import EmailCampaign
from app.models.subscription import Subscription
from app.models.user import User


@dataclass(slots=True)
class CampaignRecipient:
    user_id: str
    email: str
    full_name: str | None


class EmailCampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_all(self) -> int:
        stmt = select(func.count(EmailCampaign.id))
        return int((await self._session.execute(stmt)).scalar_one())

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[EmailCampaign]:
        stmt = (
            select(EmailCampaign)
            .order_by(EmailCampaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def get_by_id(self, campaign_id: uuid.UUID) -> EmailCampaign | None:
        return await self._session.get(EmailCampaign, campaign_id)

    async def create(
        self,
        *,
        subject: str,
        body_html: str,
        target_segment: str,
        created_by_id: uuid.UUID,
    ) -> EmailCampaign:
        campaign = EmailCampaign(
            subject=subject,
            body_html=body_html,
            target_segment=target_segment,
            created_by_id=created_by_id,
        )
        self._session.add(campaign)
        await self._session.flush()
        return campaign

    async def update_status(
        self,
        campaign: EmailCampaign,
        *,
        status: str,
        sent_count: int | None = None,
        failed_count: int | None = None,
        estimated_recipients: int | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        campaign.status = status
        if sent_count is not None:
            campaign.sent_count = sent_count
        if failed_count is not None:
            campaign.failed_count = failed_count
        if estimated_recipients is not None:
            campaign.estimated_recipients = estimated_recipients
        if sent_at is not None:
            campaign.sent_at = sent_at
        campaign.updated_at = datetime.now(UTC)

    async def delete(self, campaign: EmailCampaign) -> None:
        await self._session.delete(campaign)

    async def commit(self) -> None:
        await self._session.commit()

    # ── Recipient resolution ──────────────────────────────────────────────

    async def get_recipients(self, segment: str) -> list[CampaignRecipient]:
        """Resolve email list for a target segment."""
        if segment == "all_users":
            stmt = (
                select(User.id, User.email, User.full_name)
                .where(User.is_active.is_(True))
                .order_by(User.created_at)
            )
        elif segment == "past_due":
            stmt = (
                select(User.id, User.email, User.full_name)
                .join(Subscription, Subscription.user_id == User.id)
                .where(User.is_active.is_(True))
                .where(Subscription.status == "past_due")
                .order_by(User.created_at)
            )
        elif segment == "free_plan":
            stmt = (
                select(User.id, User.email, User.full_name)
                .join(Subscription, Subscription.user_id == User.id)
                .where(User.is_active.is_(True))
                .where(Subscription.plan_slug == "free")
                .order_by(User.created_at)
            )
        elif segment == "paid_users":
            stmt = (
                select(User.id, User.email, User.full_name)
                .join(Subscription, Subscription.user_id == User.id)
                .where(User.is_active.is_(True))
                .where(Subscription.plan_slug != "free")
                .where(Subscription.status == "active")
                .order_by(User.created_at)
            )
        elif segment == "inactive_7d":
            cutoff = datetime.now(UTC) - timedelta(days=7)
            stmt = (
                select(User.id, User.email, User.full_name)
                .where(User.is_active.is_(True))
                .where(User.updated_at < cutoff)
                .order_by(User.created_at)
            )
        else:
            return []

        rows = (await self._session.execute(stmt)).all()
        return [
            CampaignRecipient(
                user_id=str(r[0]),
                email=r[1],
                full_name=r[2],
            )
            for r in rows
        ]
