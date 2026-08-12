"""Emit append-only CRM timeline rows with consistent payloads for support tooling."""

from __future__ import annotations

import uuid
from collections.abc import Mapping

from app.models.lead_event import LeadEvent
from app.repositories.lead_event_repository import LeadEventRepository

_TEXT_CAP = 4000


def _clip_text(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if len(s) <= _TEXT_CAP:
        return s
    return s[: _TEXT_CAP - 1] + "…"


class LeadEventService:
    def __init__(self, repo: LeadEventRepository) -> None:
        self._repo = repo

    async def emit_lead_created(
        self,
        *,
        lead_id: uuid.UUID,
        bot_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        source_channel: str | None,
        creation_reason: str,
    ) -> None:
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="lead_created",
            actor_type="system",
            actor_id=None,
            old_value=None,
            new_value=None,
            metadata={
                "bot_id": str(bot_id),
                "conversation_id": str(conversation_id) if conversation_id is not None else None,
                "source_channel": source_channel,
                "creation_reason": creation_reason,
            },
        )

    async def emit_lead_status_changed(
        self,
        *,
        lead_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        old_status: str,
        new_status: str,
        old_temperature: str | None,
        new_temperature: str | None,
    ) -> None:
        meta: dict[str, object] = {}
        if old_temperature != new_temperature:
            meta["old_lead_temperature"] = old_temperature
            meta["new_lead_temperature"] = new_temperature
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="lead_status_changed",
            actor_type="user",
            actor_id=actor_user_id,
            old_value=old_status,
            new_value=new_status,
            metadata=meta or None,
        )

    async def emit_assignee_change(
        self,
        *,
        lead_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        old_assignee_id: uuid.UUID | None,
        new_assignee_id: uuid.UUID | None,
    ) -> None:
        old_s = str(old_assignee_id) if old_assignee_id is not None else None
        new_s = str(new_assignee_id) if new_assignee_id is not None else None
        is_first = old_assignee_id is None and new_assignee_id is not None
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="lead_assigned" if is_first else "lead_reassigned",
            actor_type="user",
            actor_id=actor_user_id,
            old_value=old_s,
            new_value=new_s,
            metadata=None,
        )

    async def emit_note_added(
        self,
        *,
        lead_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        previous_notes: str | None,
        new_notes: str | None,
    ) -> None:
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="note_added",
            actor_type="user",
            actor_id=actor_user_id,
            old_value=_clip_text(previous_notes),
            new_value=_clip_text(new_notes),
            metadata={
                "previous_len": len((previous_notes or "").strip()),
                "new_len": len((new_notes or "").strip()),
            },
        )

    async def emit_notification_outcome(
        self,
        *,
        lead_id: uuid.UUID,
        channel: str,
        ok: bool,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        base: dict[str, object] = {"channel": channel}
        if metadata:
            base.update(metadata)
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="notification_delivered" if ok else "notification_failed",
            actor_type="integration",
            actor_id=None,
            old_value=None,
            new_value=channel,
            metadata=base,
        )

    async def emit_lead_viewed(
        self,
        *,
        lead_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> None:
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="lead_viewed",
            actor_type="user",
            actor_id=actor_user_id,
            old_value=None,
            new_value=None,
            metadata=None,
        )

    async def list_timeline_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        lead_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LeadEvent], int]:
        items = await self._repo.list_events_for_lead_owned(
            owner_id=owner_id,
            lead_id=lead_id,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count_events_for_lead_owned(owner_id=owner_id, lead_id=lead_id)
        return items, total

    async def emit_system_action(
        self,
        *,
        lead_id: uuid.UUID,
        action: str,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        meta: dict[str, object] = {"action": action}
        if metadata:
            meta.update(metadata)
        await self._repo.insert_event(
            lead_id=lead_id,
            event_type="system_action",
            actor_type="system",
            actor_id=None,
            old_value=None,
            new_value=action,
            metadata=meta,
        )


__all__ = ["LeadEventService", "_clip_text"]
