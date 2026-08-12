"""Unit tests for :meth:`~app.services.audit_service.AuditService.log_entity_event` metadata."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


@pytest.mark.asyncio
async def test_log_entity_event_stores_metadata_json() -> None:
    session = MagicMock()
    svc = AuditService(session)
    actor = uuid.uuid4()
    eid = uuid.uuid4()
    meta = {"reason": "test", "source": "unit"}

    await svc.log_entity_event(
        actor_user_id=actor,
        action="user_suspended",
        entity_type="user",
        entity_id=eid,
        metadata_json=meta,
    )

    session.add.assert_called_once()
    row = session.add.call_args[0][0]
    assert isinstance(row, AuditLog)
    assert row.metadata_json == meta
    assert row.actor_user_id == actor
    assert row.entity_id == eid


@pytest.mark.asyncio
async def test_log_entity_event_metadata_json_optional_omitted() -> None:
    session = MagicMock()
    svc = AuditService(session)
    actor = uuid.uuid4()
    eid = uuid.uuid4()

    await svc.log_entity_event(
        actor_user_id=actor,
        action="bot_created",
        entity_type="bot",
        entity_id=eid,
    )

    row = session.add.call_args[0][0]
    assert isinstance(row, AuditLog)
    assert row.metadata_json is None
