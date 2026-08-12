"""Offline checks: Alembic revision chain for AI foundation (no database)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_FOUNDATION_REVISION = "e2f3a4b5c6d7"


def test_ai_foundation_revision_chained_under_audit_logs() -> None:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision(AI_FOUNDATION_REVISION)
    assert rev is not None
    assert rev.down_revision == "d9e1f2a3b4c5"
    head_id = script.get_current_head()
    r = script.get_revision(head_id)
    while r is not None:
        if r.revision == AI_FOUNDATION_REVISION:
            break
        down = r.down_revision
        assert down is not None, f"{AI_FOUNDATION_REVISION} not reachable from head {head_id}"
        assert not isinstance(down, tuple), "merge revisions not supported in this test"
        r = script.get_revision(down)
    assert r is not None and r.revision == AI_FOUNDATION_REVISION
