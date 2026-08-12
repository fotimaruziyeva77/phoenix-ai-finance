"""Unit tests for :mod:`app.lib.platform_moderation`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.lib.platform_moderation import bot_is_platform_suspended, user_has_platform_suspension_record


def test_user_has_platform_suspension_record() -> None:
    assert user_has_platform_suspension_record(SimpleNamespace(suspended_at=None)) is False
    assert (
        user_has_platform_suspension_record(
            SimpleNamespace(suspended_at=datetime.now(UTC)),
        )
        is True
    )


def test_bot_is_platform_suspended() -> None:
    assert bot_is_platform_suspended(SimpleNamespace(platform_suspended_at=None)) is False
    assert (
        bot_is_platform_suspended(
            SimpleNamespace(platform_suspended_at=datetime.now(UTC), id=uuid.uuid4()),
        )
        is True
    )
