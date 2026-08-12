"""
Bot API integration tests (authenticated owner-scoped CRUD).
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
def _alembic_for_bot_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def bot_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "bot-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Bot API"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    return str(data["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_bot_api_owner_scoped_crud_and_validation(bot_client: TestClient) -> None:
    owner_access = _register_and_get_access(bot_client, _unique_email("owner"))
    other_access = _register_and_get_access(bot_client, _unique_email("other"))

    # 1) POST /bots creates bot
    create_resp = bot_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_access),
        json={
            "name": "Owner Bot",
            "niche_id": "education",
            "goal_type": "support",
            "status": "active",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    bot_id = created["id"]
    assert created["name"] == "Owner Bot"
    # Service enforces safe default regardless of payload status.
    assert created["status"] == "draft"
    assert created["provider_name"] == "gemini"
    assert created["model_name"] is None
    assert created["temperature"] is None
    assert created["max_output_tokens"] is None

    # Create another bot under different owner for scoping checks.
    other_create = bot_client.post(
        "/api/v1/bots",
        headers=_auth_headers(other_access),
        json={
            "name": "Other Bot",
            "niche_id": "services",
            "goal_type": "sales",
        },
    )
    assert other_create.status_code == 201, other_create.text
    other_bot_id = other_create.json()["id"]

    # 2) GET /bots lists only current user bots
    owner_list = bot_client.get("/api/v1/bots", headers=_auth_headers(owner_access))
    assert owner_list.status_code == 200, owner_list.text
    owner_items = owner_list.json()["items"]
    assert len(owner_items) == 1
    assert owner_items[0]["id"] == bot_id
    assert owner_items[0]["name"] == "Owner Bot"

    # 3) GET /bots/{id} returns only owner bot
    owner_get = bot_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(owner_access))
    assert owner_get.status_code == 200, owner_get.text
    assert owner_get.json()["id"] == bot_id

    forbidden_get = bot_client.get(f"/api/v1/bots/{other_bot_id}", headers=_auth_headers(owner_access))
    assert forbidden_get.status_code == 403, forbidden_get.text

    # 4) PATCH updates only owner bot
    patch_owner = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={
            "name": "Owner Bot Updated",
            "status": "active",
            "welcome_message": "Hello from API patch",
            "tone": "friendly",
            "language": "en",
            "short_description": "Updated from integration test",
        },
    )
    assert patch_owner.status_code == 200, patch_owner.text
    assert patch_owner.json()["name"] == "Owner Bot Updated"
    assert patch_owner.json()["status"] == "active"
    assert patch_owner.json()["welcome_message"] == "Hello from API patch"
    assert patch_owner.json()["tone"] == "friendly"
    assert patch_owner.json()["language"] == "en"
    assert patch_owner.json()["short_description"] == "Updated from integration test"
    # Persisted values are visible on follow-up GET.
    reloaded = bot_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(owner_access))
    assert reloaded.status_code == 200, reloaded.text
    assert reloaded.json()["name"] == "Owner Bot Updated"
    assert reloaded.json()["welcome_message"] == "Hello from API patch"

    # Nullable core fields can be cleared explicitly with null.
    clear_nullable = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={
            "welcome_message": None,
            "tone": None,
            "language": None,
            "short_description": None,
        },
    )
    assert clear_nullable.status_code == 200, clear_nullable.text
    assert clear_nullable.json()["welcome_message"] is None
    assert clear_nullable.json()["tone"] is None
    assert clear_nullable.json()["language"] is None
    assert clear_nullable.json()["short_description"] is None

    # AI settings: valid PATCH persists; explicit null clears; invalid values rejected cleanly.
    ai_ok = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={
            "model_name": "gemini-2.5-flash",
            "temperature": 0.25,
            "max_output_tokens": 2048,
        },
    )
    assert ai_ok.status_code == 200, ai_ok.text
    ai_body = ai_ok.json()
    assert ai_body["model_name"] == "gemini-2.5-flash"
    assert ai_body["temperature"] == 0.25
    assert ai_body["max_output_tokens"] == 2048
    ai_reloaded = bot_client.get(f"/api/v1/bots/{bot_id}", headers=_auth_headers(owner_access))
    assert ai_reloaded.status_code == 200, ai_reloaded.text
    assert ai_reloaded.json()["model_name"] == "gemini-2.5-flash"
    assert ai_reloaded.json()["temperature"] == 0.25

    ai_clear = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={"model_name": None, "temperature": None, "max_output_tokens": None},
    )
    assert ai_clear.status_code == 200, ai_clear.text
    cleared = ai_clear.json()
    assert cleared["model_name"] is None
    assert cleared["temperature"] is None
    assert cleared["max_output_tokens"] is None

    bad_temp = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={"temperature": 5.0},
    )
    assert bad_temp.status_code == 422, bad_temp.text
    assert bad_temp.json().get("error", {}).get("code") == "validation_error"

    bad_provider_null = bot_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=_auth_headers(owner_access),
        json={"provider_name": None},
    )
    assert bad_provider_null.status_code == 422, bad_provider_null.text
    assert bad_provider_null.json().get("error", {}).get("code") == "bot_validation_error"

    patch_forbidden = bot_client.patch(
        f"/api/v1/bots/{other_bot_id}",
        headers=_auth_headers(owner_access),
        json={"name": "Hacked"},
    )
    assert patch_forbidden.status_code == 403, patch_forbidden.text

    # 5) archive works
    archive_owner = bot_client.post(
        f"/api/v1/bots/{bot_id}/archive",
        headers=_auth_headers(owner_access),
    )
    assert archive_owner.status_code == 200, archive_owner.text
    assert archive_owner.json()["status"] == "archived"
    # Archived bots remain visible for clean lifecycle UX (status badge in list).
    owner_list_after_archive = bot_client.get("/api/v1/bots", headers=_auth_headers(owner_access))
    assert owner_list_after_archive.status_code == 200, owner_list_after_archive.text
    owner_items_after_archive = owner_list_after_archive.json()["items"]
    assert any(item["id"] == bot_id and item["status"] == "archived" for item in owner_items_after_archive)

    archive_forbidden = bot_client.post(
        f"/api/v1/bots/{other_bot_id}/archive",
        headers=_auth_headers(owner_access),
    )
    assert archive_forbidden.status_code == 403, archive_forbidden.text

    # 6) unauthorized requests fail
    unauth = bot_client.get("/api/v1/bots")
    assert unauth.status_code == 401, unauth.text

    # 7) invalid niche or goal_type returns clean error
    invalid_niche = bot_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_access),
        json={
            "name": "Bad Niche Bot",
            "niche_id": "unknown_niche",
            "goal_type": "support",
        },
    )
    assert invalid_niche.status_code == 422, invalid_niche.text
    niche_body = invalid_niche.json()
    assert niche_body.get("error", {}).get("code") in {"bot_validation_error", "validation_error"}

    invalid_goal = bot_client.post(
        "/api/v1/bots",
        headers=_auth_headers(owner_access),
        json={
            "name": "Bad Goal Bot",
            "niche_id": "education",
            "goal_type": "not_supported",
        },
    )
    assert invalid_goal.status_code == 422, invalid_goal.text
    goal_body = invalid_goal.json()
    assert goal_body.get("error", {}).get("code") in {"bot_validation_error", "validation_error"}
