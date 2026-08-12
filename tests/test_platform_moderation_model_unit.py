"""ORM model shape checks for platform moderation fields (no database)."""

from __future__ import annotations

from app.models.audit_log import AuditLog
from app.models.bot import Bot
from app.models.user import User
from app.schemas.user import UserRead
from sqlalchemy import inspect


def test_user_model_maps_suspension_columns() -> None:
    cols = {c.key for c in inspect(User).mapper.column_attrs}
    assert "suspended_at" in cols
    assert "suspension_reason" in cols


def test_bot_model_maps_platform_suspension_columns() -> None:
    cols = {c.key for c in inspect(Bot).mapper.column_attrs}
    assert "platform_suspended_at" in cols
    assert "platform_suspension_reason" in cols


def test_audit_log_model_maps_metadata_json() -> None:
    cols = {c.key for c in inspect(AuditLog).mapper.column_attrs}
    assert "metadata_json" in cols


def test_user_read_api_omits_internal_moderation_fields() -> None:
    """Public profile stays stable; suspension details are superadmin/internal only."""
    names = set(UserRead.model_fields.keys())
    assert "suspended_at" not in names
    assert "suspension_reason" not in names
