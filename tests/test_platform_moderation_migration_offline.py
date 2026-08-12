"""Offline Alembic chain check for platform moderation migration."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_MODERATION_REVISION = "z9y8x7w6v5u4"
TELEGRAM_CONVERSATION_CHAT_ID_REVISION = "w9x0y1z2a3b4"


def test_platform_moderation_migration_chains_from_telegram_conversation_revision() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(PLATFORM_MODERATION_REVISION)
    assert rev is not None
    assert rev.down_revision == TELEGRAM_CONVERSATION_CHAT_ID_REVISION
