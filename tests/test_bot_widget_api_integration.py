"""
Owner widget config API integration tests (auth + owner scoping + validation).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from fastapi.testclient import TestClient

from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


def _alembic_upgrade_head(url: str) -> None:
    prev = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        if prev is not None:
            os.environ["DATABASE_URL"] = prev
        else:
            os.environ.pop("DATABASE_URL", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_bot_widget_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def widget_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "widget-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Widget API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str, *, name: str = "W Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={
            "name": name,
            "niche_id": "education",
            "goal_type": "support",
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_owner_can_fetch_widget_config(widget_client: TestClient) -> None:
    access = _register_and_get_access(widget_client, _unique_email("fetch"))
    bot_id = _create_bot(widget_client, access)

    r = widget_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bot_id"] == bot_id
    assert "public_widget_key" in body
    assert len(body["public_widget_key"]) >= 40
    assert body["is_enabled"] is True
    assert body["allowed_domains"] == []
    assert body.get("theme") is None
    assert body.get("welcome_text") is None
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_owner_can_update_widget_config_and_public_key_unchanged(widget_client: TestClient) -> None:
    access = _register_and_get_access(widget_client, _unique_email("patch"))
    bot_id = _create_bot(widget_client, access)

    first = widget_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert first.status_code == 200, first.text
    key1 = first.json()["public_widget_key"]

    patch = widget_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={
            "allowed_domains_json": ["HTTPS://WWW.Example.COM/app", "cdn.partner.org"],
            "is_enabled": False,
            "theme": "dark",
            "welcome_text": "Hello from widget",
        },
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["public_widget_key"] == key1
    assert body["is_enabled"] is False
    assert body["allowed_domains"] == ["www.example.com", "cdn.partner.org"]
    assert body["theme"] == "dark"
    assert body["welcome_text"] == "Hello from widget"

    second = widget_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert second.status_code == 200, second.text
    assert second.json()["public_widget_key"] == key1
    assert second.json()["allowed_domains"] == ["www.example.com", "cdn.partner.org"]


def test_non_owner_cannot_access_another_bot_widget_config(widget_client: TestClient) -> None:
    owner_a = _register_and_get_access(widget_client, _unique_email("wa"))
    owner_b = _register_and_get_access(widget_client, _unique_email("wb"))
    bot_a = _create_bot(widget_client, owner_a, name="A Bot")

    for method, path, kwargs in (
        (
            "get",
            f"/api/v1/bots/{bot_a}/widget",
            {},
        ),
        (
            "patch",
            f"/api/v1/bots/{bot_a}/widget",
            {"json": {"is_enabled": True}},
        ),
    ):
        fn = getattr(widget_client, method)
        r = fn(path, headers=_auth_headers(owner_b), **kwargs)
        assert r.status_code == 403, r.text
        err = r.json().get("error", {})
        assert err.get("code") == "bot_forbidden"


def test_invalid_domain_input_returns_clean_error(widget_client: TestClient) -> None:
    access = _register_and_get_access(widget_client, _unique_email("bad-dom"))
    bot_id = _create_bot(widget_client, access)

    r = widget_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"allowed_domains_json": [""]},
    )
    assert r.status_code == 422, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "validation_error"
    details = err.get("details")
    assert isinstance(details, list)
    assert len(details) >= 1


def test_widget_endpoints_require_auth(widget_client: TestClient) -> None:
    access = _register_and_get_access(widget_client, _unique_email("unauth"))
    bot_id = _create_bot(widget_client, access)

    r_get = widget_client.get(f"/api/v1/bots/{bot_id}/widget")
    assert r_get.status_code == 401, r_get.text

    r_patch = widget_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        json={"is_enabled": False},
    )
    assert r_patch.status_code == 401, r_patch.text


def test_public_widget_key_returned_and_matches_between_get_and_patch(widget_client: TestClient) -> None:
    access = _register_and_get_access(widget_client, _unique_email("key-check"))
    bot_id = _create_bot(widget_client, access)

    g = widget_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert g.status_code == 200, g.text
    key = g.json()["public_widget_key"]
    assert all(c.isalnum() or c in "-_" for c in key)

    p = widget_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"theme": "light"},
    )
    assert p.status_code == 200, p.text
    assert p.json()["public_widget_key"] == key


def test_wildcard_allowlist_rejected_when_wildcard_patterns_disabled(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS", "false")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            access = _register_and_get_access(client, _unique_email("wild-off"))
            bot_id = _create_bot(client, access)
            r = client.patch(
                f"/api/v1/bots/{bot_id}/widget",
                headers=_auth_headers(access),
                json={"allowed_domains_json": ["*.embed.example"]},
            )
            assert r.status_code == 422, r.text
            assert r.json().get("error", {}).get("code") == "widget_config_validation_error"
    finally:
        asyncio.run(dispose_engine())
        monkeypatch.delenv("APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS", raising=False)
        get_settings.cache_clear()
