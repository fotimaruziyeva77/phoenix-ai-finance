"""Timeline no-op implementation for tests that stub :class:`~app.repositories.lead_repository.LeadRepository`."""

from __future__ import annotations

import uuid

from app.models.lead_event import LeadEvent


class NoopLeadEventService:
    async def emit_lead_created(self, **_kw: object) -> None:
        return None

    async def emit_lead_viewed(self, **_kw: object) -> None:
        return None

    async def list_timeline_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LeadEvent], int]:
        return [], 0

    async def emit_lead_status_changed(self, **_kw: object) -> None:
        return None

    async def emit_assignee_change(self, **_kw: object) -> None:
        return None

    async def emit_note_added(self, **_kw: object) -> None:
        return None

    async def emit_notification_outcome(self, **_kw: object) -> None:
        return None

    async def emit_system_action(self, **_kw: object) -> None:
        return None


NOOP_LEAD_EVENT_SERVICE = NoopLeadEventService()

__all__ = ["NOOP_LEAD_EVENT_SERVICE", "NoopLeadEventService"]
