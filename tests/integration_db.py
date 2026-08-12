"""PostgreSQL URL resolution for integration tests run on the dev host."""

from __future__ import annotations

import os


def integration_database_url() -> str | None:
    """
    URL for pytest integration tests.

    - ``TEST_DATABASE_URL`` always wins (use for CI / explicit host-reachable DB).
    - ``DATABASE_URL`` is used only if it looks host-reachable: URLs containing
      ``@postgres:`` target the Compose service name from *inside* the Docker
      network and fail from the host, so they are ignored unless overridden above.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit
    u = os.environ.get("DATABASE_URL")
    if not u:
        return None
    if "@postgres:" in u:
        return None
    return u
