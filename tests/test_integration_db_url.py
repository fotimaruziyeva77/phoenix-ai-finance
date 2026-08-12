"""integration_database_url() resolution (no live DB)."""

from tests.integration_db import integration_database_url


def test_prefers_test_database_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://u:p@postgres:5432/ignored"
    )
    monkeypatch.setenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/app"
    )
    assert integration_database_url() == "postgresql+asyncpg://u:p@127.0.0.1:5432/app"


def test_skips_compose_service_hostname_without_test_override(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://u:p@postgres:5432/app"
    )
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    assert integration_database_url() is None


def test_uses_host_reachable_database_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://u:p@127.0.0.1:5432/app"
    )
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    assert integration_database_url() == "postgresql+asyncpg://u:p@127.0.0.1:5432/app"
