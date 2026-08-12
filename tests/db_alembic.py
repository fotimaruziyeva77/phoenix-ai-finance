"""Shared Alembic ``upgrade head`` for integration tests (avoids copy-paste per module)."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.config import get_settings


def run_alembic_upgrade_head(*, database_url: str, project_root: Path) -> None:
    """Point Alembic at ``database_url``, migrate to head, restore prior ``DATABASE_URL``."""
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        cfg = Config(str(project_root / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()
