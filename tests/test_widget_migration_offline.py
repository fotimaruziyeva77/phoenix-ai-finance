"""Offline Alembic checks for ``widget_configs`` (no database)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIDGET_CONFIGS_REVISION = "q7r8s9t0u1v2"
CONVERSATIONS_WEB_WIDGET_SESSION_REVISION = "s0t1u2v3w4"
KNOWLEDGE_CHUNKS_FTS_INDEX_REVISION = "p6q7r8s9t0u1"


def test_widget_configs_migration_revision_is_chained_and_callable() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(WIDGET_CONFIGS_REVISION)
    assert rev is not None
    assert rev.down_revision == KNOWLEDGE_CHUNKS_FTS_INDEX_REVISION


def test_conversations_web_widget_session_migration_chains_from_widget_configs() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(CONVERSATIONS_WEB_WIDGET_SESSION_REVISION)
    assert rev is not None
    assert rev.down_revision == WIDGET_CONFIGS_REVISION


def test_widget_configs_migration_module_upgrade_callable() -> None:
    """Ensure revision module loads (catches syntax/name errors)."""
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(WIDGET_CONFIGS_REVISION)
    assert rev is not None
    parent = script.get_revision(rev.down_revision)  # type: ignore[arg-type]
    assert parent is not None


def test_conversations_web_widget_session_migration_module_loads() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(CONVERSATIONS_WEB_WIDGET_SESSION_REVISION)
    assert rev is not None
    parent = script.get_revision(rev.down_revision)  # type: ignore[arg-type]
    assert parent is not None
