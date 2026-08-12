"""Create dashboard notifications for bot owners on key events (lead capture, etc.)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.repositories.notification_repository import NotificationRepository

if TYPE_CHECKING:
    from app.models.bot import Bot
    from app.models.lead import Lead

_LOG = get_logger("owner_notification")


class OwnerNotificationService:
    """Thin facade — create notifications and query counts."""

    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def notify_new_lead(
        self,
        *,
        owner_id: uuid.UUID,
        bot: "Bot",
        lead: "Lead",
    ) -> None:
        """Create a dashboard notification for a newly captured lead."""
        bot_name = (bot.name or "").strip() or "Bot"
        lead_name = (getattr(lead, "name", None) or "").strip()
        phone = (getattr(lead, "phone", None) or "").strip()

        fallback_name = "Nomalum"
        title = f"Yangi lead: {lead_name or phone or fallback_name}"
        body_parts = [f"Bot: {bot_name}"]
        if lead_name:
            body_parts.append(f"Ism: {lead_name}")
        if phone:
            body_parts.append(f"Telefon: {phone}")
        summary = (getattr(lead, "summary", None) or "").strip()
        if summary:
            body_parts.append(summary[:200])
        body = "\n".join(body_parts)

        try:
            await self._repo.create(
                owner_id=owner_id,
                kind="new_lead",
                title=title[:256],
                body=body[:2048] if body else None,
                reference_id=lead.id,
                reference_type="lead",
            )
        except Exception:
            _LOG.warning(
                "owner_notification_create_failed",
                exc_info=True,
                owner_id=str(owner_id),
                lead_id=str(lead.id),
            )

    async def count_unread(self, owner_id: uuid.UUID) -> int:
        return await self._repo.count_unread(owner_id)

    async def list_recent(
        self,
        owner_id: uuid.UUID,
        *,
        limit: int = 30,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list:
        return await self._repo.list_recent(
            owner_id, limit=limit, offset=offset, unread_only=unread_only
        )

    async def mark_read(self, owner_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        return await self._repo.mark_read(owner_id, notification_id)

    async def mark_all_read(self, owner_id: uuid.UUID) -> int:
        return await self._repo.mark_all_read(owner_id)
