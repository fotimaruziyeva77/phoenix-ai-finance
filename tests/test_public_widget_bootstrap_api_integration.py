"""
Public widget bootstrap API integration tests (no auth; Origin/Referer + allowlist).
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
from tests.public_widget_paths import public_widget_bootstrap_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32

_SAFE_BOOTSTRAP_KEYS = frozenset({"is_enabled", "welcome_text", "theme", "bot_display_name"})
_ORIGIN_FORBIDDEN_MESSAGE = "This widget cannot be loaded from this site."


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
def _alembic_for_public_bootstrap_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def bootstrap_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "bootstrap-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Bootstrap API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str, *, name: str) -> str:
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


def test_valid_key_returns_safe_config_without_private_fields(bootstrap_client: TestClient) -> None:
    access = _register_and_get_access(bootstrap_client, _unique_email("safe"))
    bot_id = _create_bot(bootstrap_client, access, name="Public Bot Title")
    w = bootstrap_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert w.status_code == 200, w.text
    public_key = w.json()["public_widget_key"]

    patch = bootstrap_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={
            "welcome_text": "Hi visitor",
            "theme": "dark",
        },
    )
    assert patch.status_code == 200, patch.text

    # Empty allowlist: Origin optional
    r = bootstrap_client.get(public_widget_bootstrap_path(public_key))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == _SAFE_BOOTSTRAP_KEYS
    assert body["is_enabled"] is True
    assert body["welcome_text"] == "Hi visitor"
    assert body["theme"] == "dark"
    assert body["bot_display_name"] == "Public Bot Title"

    for leak in (
        "owner_id",
        "bot_id",
        "public_widget_key",
        "id",
        "allowed_domains",
        "allowed_domains_json",
        "widget_settings",
        "widget_settings_json",
        "email",
        "password",
        "niche_id",
        "goal_type",
        "provider_name",
        "model_name",
    ):
        assert leak not in body


def test_disabled_widget_returns_forbidden_without_leaking_details(bootstrap_client: TestClient) -> None:
    access = _register_and_get_access(bootstrap_client, _unique_email("dis"))
    bot_id = _create_bot(bootstrap_client, access, name="Disabled Bot")
    w = bootstrap_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert w.status_code == 200, w.text
    public_key = w.json()["public_widget_key"]

    off = bootstrap_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"is_enabled": False},
    )
    assert off.status_code == 200, off.text

    r = bootstrap_client.get(public_widget_bootstrap_path(public_key))
    assert r.status_code == 403, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "widget_disabled"
    assert "owner" not in err.get("message", "").lower()


def test_invalid_widget_key_returns_not_found(bootstrap_client: TestClient) -> None:
    fake_key = "x" * 43
    r = bootstrap_client.get(public_widget_bootstrap_path(fake_key))
    assert r.status_code == 404, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "widget_not_found"


def test_allowlist_requires_matching_origin(bootstrap_client: TestClient) -> None:
    access = _register_and_get_access(bootstrap_client, _unique_email("origin"))
    bot_id = _create_bot(bootstrap_client, access, name="Origin Bot")
    w = bootstrap_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    assert w.status_code == 200, w.text
    public_key = w.json()["public_widget_key"]

    up = bootstrap_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"allowed_domains_json": ["embed.customer.test"]},
    )
    assert up.status_code == 200, up.text

    bad = bootstrap_client.get(
        public_widget_bootstrap_path(public_key),
        headers={"Origin": "https://evil.test"},
    )
    assert bad.status_code == 403, bad.text
    err_bad = bad.json().get("error", {})
    assert err_bad.get("code") == "widget_origin_forbidden"
    assert err_bad.get("message") == _ORIGIN_FORBIDDEN_MESSAGE

    no_origin = bootstrap_client.get(public_widget_bootstrap_path(public_key))
    assert no_origin.status_code == 403, no_origin.text
    err_no = no_origin.json().get("error", {})
    assert err_no.get("code") == "widget_origin_forbidden"
    assert err_no.get("message") == _ORIGIN_FORBIDDEN_MESSAGE

    good = bootstrap_client.get(
        public_widget_bootstrap_path(public_key),
        headers={"Origin": "https://embed.customer.test"},
    )
    assert good.status_code == 200, good.text
    assert good.json()["bot_display_name"] == "Origin Bot"
    assert set(good.json().keys()) == _SAFE_BOOTSTRAP_KEYS


def test_empty_allowlist_bootstrap_forbidden_when_force_deny_empty(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST", "true")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            access = _register_and_get_access(client, _unique_email("deny-empty"))
            bot_id = _create_bot(client, access, name="Deny Empty Bot")
            w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
            assert w.status_code == 200, w.text
            public_key = w.json()["public_widget_key"]

            r = client.get(public_widget_bootstrap_path(public_key))
            assert r.status_code == 403, r.text
            err = r.json().get("error", {})
            assert err.get("code") == "widget_origin_forbidden"
            assert err.get("message") == _ORIGIN_FORBIDDEN_MESSAGE
    finally:
        asyncio.run(dispose_engine())
        monkeypatch.delenv("APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST", raising=False)
        get_settings.cache_clear()


def test_allowlist_accepts_referer_when_origin_absent(bootstrap_client: TestClient) -> None:
    access = _register_and_get_access(bootstrap_client, _unique_email("ref"))
    bot_id = _create_bot(bootstrap_client, access, name="Ref Bot")
    w = bootstrap_client.get(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
    )
    public_key = w.json()["public_widget_key"]

    bootstrap_client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"allowed_domains_json": ["app.referer.test"]},
    )

    r = bootstrap_client.get(
        public_widget_bootstrap_path(public_key),
        headers={"Referer": "https://app.referer.test/dashboard?x=1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["bot_display_name"] == "Ref Bot"
