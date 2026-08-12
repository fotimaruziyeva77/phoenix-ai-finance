"""Offline Alembic checks for ``telegram_configs`` (no database)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEGRAM_CONFIGS_REVISION = "u1v2w3x4y5z6"
TELEGRAM_WEBHOOK_SECRET_REVISION = "v8w9x0y1z2a3"
TELEGRAM_CONVERSATION_CHAT_ID_REVISION = "w9x0y1z2a3b4"
CONVERSATIONS_WEB_WIDGET_SESSION_REVISION = "s0t1u2v3w4"
REFRESH_SESSIONS_REVISION = "a1b2c3d4e5f8"
TELEGRAM_PROVISIONING_STATUS_REVISION = "b2c3d4e5f6a7"


def test_telegram_configs_migration_chains_from_conversations_web_widget_revision() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(TELEGRAM_CONFIGS_REVISION)
    assert rev is not None
    assert rev.down_revision == CONVERSATIONS_WEB_WIDGET_SESSION_REVISION


def test_telegram_configs_migration_module_loads_and_upgrade_callable() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(TELEGRAM_CONFIGS_REVISION)
    assert rev is not None
    parent = script.get_revision(rev.down_revision)  # type: ignore[arg-type]
    assert parent is not None


def test_telegram_webhook_secret_migration_chains_from_telegram_configs() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(TELEGRAM_WEBHOOK_SECRET_REVISION)
    assert rev is not None
    assert rev.down_revision == TELEGRAM_CONFIGS_REVISION


def test_conversations_telegram_chat_id_migration_chains_from_webhook_secret() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(TELEGRAM_CONVERSATION_CHAT_ID_REVISION)
    assert rev is not None
    assert rev.down_revision == TELEGRAM_WEBHOOK_SECRET_REVISION


def test_telegram_provisioning_status_migration_chains_from_refresh_sessions() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(TELEGRAM_PROVISIONING_STATUS_REVISION)
    assert rev is not None
    assert rev.down_revision == REFRESH_SESSIONS_REVISION
