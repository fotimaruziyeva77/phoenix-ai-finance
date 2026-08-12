"""Minimal DB-backed audit hooks for domain lifecycle events."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

BOT_ENTITY_TYPE = "bot"
BOT_ACTION_CREATED = "bot_created"
BOT_ACTION_UPDATED = "bot_updated"
BOT_ACTION_ARCHIVED = "bot_archived"
BOT_ACTION_DELETED = "bot_deleted"

USER_ENTITY_TYPE = "user"
USER_ACTION_SUSPENDED = "user_suspended"
USER_ACTION_UNSUSPENDED = "user_unsuspended"
USER_ACTION_UPDATED = "user_updated"

BOT_ACTION_PLATFORM_SUSPENDED = "bot_platform_suspended"
BOT_ACTION_PLATFORM_UNSUSPENDED = "bot_platform_unsuspended"

TENANT_ENTITY_TYPE = "tenant"
TENANT_ACTION_SUPERADMIN_INSPECT = "superadmin_tenant_inspect"


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_entity_event(
        self,
        *,
        actor_user_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        event = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            metadata_json=metadata_json,
        )
        self._session.add(event)


def bot_audit_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Restrict snapshots to safe bot lifecycle fields.
    Avoid adding secrets/tokens here.
    """
    allowed = (
        "id",
        "owner_id",
        "name",
        "niche_id",
        "goal_type",
        "status",
        "welcome_message",
        "tone",
        "language",
        "short_description",
        "provider_name",
        "model_name",
        "temperature",
        "max_output_tokens",
        "updated_at",
        "platform_suspended_at",
        "platform_suspension_reason",
    )
    out: dict[str, Any] = {}
    for key in allowed:
        value = payload.get(key)
        if isinstance(value, (uuid.UUID, datetime)):
            out[key] = str(value)
        else:
            out[key] = value
    return out
