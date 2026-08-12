"""Pytest wiring for ``tests/integration`` (PostgreSQL + Alembic)."""

from __future__ import annotations

import pytest

pytest_plugins = ["tests.integration.auth_fixtures"]

from tests.integration.auth_setup import alembic_upgrade_head
from tests.integration_db import integration_database_url


def _require_db_url() -> str:
    u = integration_database_url()
    if not u:
        pytest.skip(
            "Set TEST_DATABASE_URL or a host-reachable DATABASE_URL "
            "(Compose URLs with @postgres: are ignored on the host)."
        )
    return u


pytestmark = [
    pytest.mark.skipif(
        integration_database_url() is None,
        reason="No TEST_DATABASE_URL / host DATABASE_URL configured.",
    ),
]


@pytest.fixture(scope="module")
def live_db_url() -> str:
    return _require_db_url()


@pytest.fixture(scope="module", autouse=True)
def _alembic_upgrade_for_integration_module(live_db_url: str) -> None:
    alembic_upgrade_head(live_db_url)
