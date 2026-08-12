"""
Architecture consistency for unified multi-channel conversations (no DB).

Guards: channel registry, single external-thread lookup API, adapters do not import
sales orchestration directly (orchestration stays in AIService).
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.lib.chat_channels import (
    CONVERSATION_CHANNEL_ADMIN_TEST,
    CONVERSATION_CHANNEL_TELEGRAM,
    CONVERSATION_CHANNEL_WEB_WIDGET,
    KNOWN_CONVERSATION_CHANNELS,
    is_registered_conversation_channel,
)
from app.repositories.ai_chat_repository import AIChatRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _service_modules_that_must_not_import_orchestrator() -> list[Path]:
    return [
        PROJECT_ROOT / "app" / "services" / "telegram_webhook_inbound_service.py",
        PROJECT_ROOT / "app" / "services" / "public_widget_chat_service.py",
        PROJECT_ROOT / "app" / "services" / "web_widget_session_service.py",
        PROJECT_ROOT / "app" / "services" / "conversation_thread_service.py",
    ]


def _imported_app_service_modules(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("app.services."):
                out.add(node.module)
    return out


@pytest.mark.parametrize(
    "path",
    _service_modules_that_must_not_import_orchestrator(),
    ids=lambda p: p.name,
)
def test_channel_adapters_do_not_import_sales_orchestrator_module(path: Path) -> None:
    """Sales stack is reached only via AIService.send_bot_message, not a second import graph."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = _imported_app_service_modules(tree)
    assert "app.services.sales_conversation_orchestrator" not in modules


def test_ai_service_imports_sales_orchestrator_for_centralized_turns() -> None:
    path = PROJECT_ROOT / "app" / "services" / "ai_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = _imported_app_service_modules(tree)
    assert "app.services.sales_conversation_orchestrator" in modules


def test_known_conversation_channels_include_all_ingress_keys() -> None:
    assert CONVERSATION_CHANNEL_ADMIN_TEST in KNOWN_CONVERSATION_CHANNELS
    assert CONVERSATION_CHANNEL_WEB_WIDGET in KNOWN_CONVERSATION_CHANNELS
    assert CONVERSATION_CHANNEL_TELEGRAM in KNOWN_CONVERSATION_CHANNELS
    assert is_registered_conversation_channel(CONVERSATION_CHANNEL_WEB_WIDGET)
    assert is_registered_conversation_channel(" slack ") is False


@pytest.mark.asyncio
async def test_get_active_conversation_for_channel_rejects_unregistered_lookup() -> None:
    repo = AIChatRepository(AsyncMock())
    with pytest.raises(ValueError, match="Unsupported channel"):
        await repo.get_active_conversation_for_channel(
            bot_id=uuid.uuid4(),
            channel="admin_test",
            public_visitor_session_key="a" * 16,
        )


@pytest.mark.asyncio
async def test_get_active_conversation_for_channel_web_widget_requires_key() -> None:
    repo = AIChatRepository(AsyncMock())
    with pytest.raises(ValueError, match="web_widget requires"):
        await repo.get_active_conversation_for_channel(
            bot_id=uuid.uuid4(),
            channel=CONVERSATION_CHANNEL_WEB_WIDGET,
            public_visitor_session_key=None,
        )


@pytest.mark.asyncio
async def test_get_active_conversation_for_channel_telegram_requires_chat_id() -> None:
    repo = AIChatRepository(AsyncMock())
    with pytest.raises(ValueError, match="telegram requires"):
        await repo.get_active_conversation_for_channel(
            bot_id=uuid.uuid4(),
            channel=CONVERSATION_CHANNEL_TELEGRAM,
            telegram_chat_id=None,
        )
