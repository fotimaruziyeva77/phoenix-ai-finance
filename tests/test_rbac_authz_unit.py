"""Authorization unit tests: owner-scoped services vs superadmin role (no database)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.enums import UserRole
from app.services.bot_exceptions import BotForbiddenError
from app.services.bot_service import BotService


@pytest.mark.asyncio
async def test_superadmin_still_forbidden_for_other_owners_bot() -> None:
    """
    Privilege escalation guard: ``UserRole.superadmin`` must not bypass ``owner_id`` in
    :meth:`~app.services.bot_service.BotService.get_bot_for_user` (cross-tenant admin is a
    separate API surface).
    """
    repo = MagicMock()
    repo.get_bot_by_id = AsyncMock(return_value=None)
    repo.exists_by_id = AsyncMock(return_value=True)
    svc = BotService(repo, audit_service=None)
    superadmin = SimpleNamespace(id=uuid.uuid4(), role=UserRole.superadmin)
    foreign_bot_id = uuid.uuid4()
    with pytest.raises(BotForbiddenError):
        await svc.get_bot_for_user(superadmin, foreign_bot_id)
    repo.get_bot_by_id.assert_awaited_once_with(owner_id=superadmin.id, bot_id=foreign_bot_id)


