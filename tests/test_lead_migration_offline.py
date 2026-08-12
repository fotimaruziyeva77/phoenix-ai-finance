"""Offline migration checks for ``leads`` (no database)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEADS_TABLE_REVISION = "h8i9j0k1l2m3"
LEADS_CONV_UNIQUE_INDEX_REVISION = "i9j0k1l2m3n4"
PREVIOUS_AFTER_CONV_FLOW = "g7h8i9j0k1l2"


def test_leads_table_migration_revision_is_chained_and_callable() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(LEADS_TABLE_REVISION)
    assert rev is not None
    assert rev.down_revision == PREVIOUS_AFTER_CONV_FLOW
    assert callable(rev.module.upgrade)
    assert callable(rev.module.downgrade)


def test_leads_conversation_unique_index_migration_is_chained_and_callable() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(LEADS_CONV_UNIQUE_INDEX_REVISION)
    assert rev is not None
    assert rev.down_revision == LEADS_TABLE_REVISION
    assert callable(rev.module.upgrade)
    assert callable(rev.module.downgrade)
