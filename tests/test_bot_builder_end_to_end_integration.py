"""
End-to-end integration coverage for the bot builder against the real FastAPI stack and PostgreSQL.

Flow mirrored from the UI wizard:

1. Load niche catalog → pick a visible niche and a supported goal.
2. Submit “basics” (name, niche, goal, copy fields) → draft bot when no ``initial_channel``.
3. Branch on channel: ``web`` activates immediately; ``telegram`` without token stays ``channel_pending``;
   ``telegram``/``both`` with a syntactically valid token (verified by an **offline** stub for Telegram getMe/setWebhook)
   becomes ``active`` with a connected ``telegram_configs`` row.
4. Review step: ``GET /bots/{id}`` and list must match persisted ``bots`` rows.
5. Finalize draft: ``PATCH`` to ``active`` when no Telegram primary channel is required.

**State assertions:** Each scenario compares the HTTP JSON to rows read back via SQLAlchemy in a **separate** session
(so we prove persistence, not just in-memory response shaping).

**External stubs:** Telegram Bot API is not called on the network; :func:`tests.bot_builder_integration_support.stub_verify_telegram_token`
and no-op webhook helpers are injected only through ``get_telegram_config_service``. Bot service logic and DB commits are not mocked.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE, TELEGRAM_PROVISIONING_CHANNEL_PENDING
from app.main import app
from fastapi.testclient import TestClient

from tests.bot_builder_integration_support import (
    DEFAULT_PUBLIC_API_BASE_INTEGRATION,
    DEFAULT_VALID_TELEGRAM_TOKEN_FOR_TESTS,
    TELEGRAM_FERNET_INTEGRATION_KEY,
    alembic_upgrade_head,
    attach_telegram_override,
    auth_headers,
    builder_client_teardown,
    count_bots_for_owner,
    fetch_bot_row,
    fetch_telegram_config_row,
    pick_visible_niche_and_goal,
    unique_email,
)
from tests.integration_db import integration_database_url

JWT_BUILDER_E2E_KEY = "w" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL or a host-reachable DATABASE_URL "
            "(not @postgres: from the host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_builder_e2e() -> None:
    url = _integration_db_url()
    assert url is not None
    alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def builder_e2e_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_BUILDER_E2E_KEY)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", TELEGRAM_FERNET_INTEGRATION_KEY)
    monkeypatch.setenv("APP_PUBLIC_API_BASE_URL", DEFAULT_PUBLIC_API_BASE_INTEGRATION)
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    attach_telegram_override()
    with TestClient(app) as client:
        yield client
    builder_client_teardown()


def _register(client: TestClient, prefix: str) -> tuple[str, uuid.UUID]:
    email = unique_email(prefix)
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Builder E2E"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return str(body["access_token"]), uuid.UUID(body["user"]["id"])


def _assert_bot_api_matches_db(
    *,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    api_bot: dict,
    bot_id: uuid.UUID,
) -> None:
    row = asyncio.run(fetch_bot_row(live_db_url, monkeypatch, bot_id))
    assert row is not None
    assert str(row.id) == api_bot["id"]
    assert row.name == api_bot["name"]
    assert row.niche_id == api_bot["niche_id"]
    assert row.goal_type == api_bot["goal_type"]
    assert row.status == api_bot["status"]
    assert row.primary_channel == api_bot.get("primary_channel")
    assert row.welcome_message == api_bot.get("welcome_message")
    assert row.short_description == api_bot.get("short_description")


def test_catalog_niche_goal_basics_draft_persisted(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cat = builder_e2e_client.get("/api/v1/catalog/niches")
    assert cat.status_code == 200, cat.text
    niche_id, goal_type = pick_visible_niche_and_goal(cat.json())

    access, _owner = _register(builder_e2e_client, "draft_flow")
    basics = {
        "name": "Draft From Catalog",
        "niche_id": niche_id,
        "goal_type": goal_type,
        "welcome_message": "Hi — how can we help?",
        "tone": "friendly",
        "language": "en",
        "short_description": "E2E draft bot",
    }
    create = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json=basics,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    bot_id = uuid.UUID(body["id"])
    assert body["status"] == "draft"
    assert body.get("primary_channel") is None
    assert body["niche_id"] == niche_id
    assert body["goal_type"] == goal_type

    _assert_bot_api_matches_db(live_db_url=live_db_url, monkeypatch=monkeypatch, api_bot=body, bot_id=bot_id)

    listed = builder_e2e_client.get("/api/v1/bots", headers=auth_headers(access))
    assert listed.status_code == 200
    hit = next(x for x in listed.json()["items"] if x["id"] == str(bot_id))
    assert hit["status"] == "draft"
    assert hit["primary_channel"] is None


def test_draft_review_patch_active_finalizes_without_telegram_channel(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "finalize_draft")
    create = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "Finalize Me",
            "niche_id": "education",
            "goal_type": "consulting",
            "short_description": "Review then activate",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = uuid.UUID(create.json()["id"])
    assert create.json()["status"] == "draft"

    patch = builder_e2e_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=auth_headers(access),
        json={"status": "active"},
    )
    assert patch.status_code == 200, patch.text
    active_body = patch.json()
    assert active_body["status"] == "active"

    get_one = builder_e2e_client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers(access))
    assert get_one.json()["status"] == "active"

    _assert_bot_api_matches_db(
        live_db_url=live_db_url,
        monkeypatch=monkeypatch,
        api_bot=active_body,
        bot_id=bot_id,
    )


def test_web_channel_path_active_and_telegram_stays_draft(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "web_path")
    r = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "Web Channel Bot",
            "niche_id": "services",
            "goal_type": "sales",
            "initial_channel": "web",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    bot_id = uuid.UUID(body["id"])
    assert body["status"] == "active"
    assert body["primary_channel"] == "web"

    _assert_bot_api_matches_db(live_db_url=live_db_url, monkeypatch=monkeypatch, api_bot=body, bot_id=bot_id)

    tg = builder_e2e_client.get(
        f"/api/v1/bots/{bot_id}/telegram/status",
        headers=auth_headers(access),
    )
    assert tg.status_code == 200
    assert tg.json()["channel_status"] == "draft"

    row = asyncio.run(fetch_telegram_config_row(live_db_url, monkeypatch, bot_id))
    assert row is None


def test_telegram_without_token_channel_pending_db_and_api(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "tg_pending")
    r = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "TG Pending",
            "niche_id": "healthcare",
            "goal_type": "faq",
            "initial_channel": "telegram",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    bot_id = uuid.UUID(body["id"])
    assert body["status"] == "channel_pending"
    assert body["primary_channel"] == "telegram"

    _assert_bot_api_matches_db(live_db_url=live_db_url, monkeypatch=monkeypatch, api_bot=body, bot_id=bot_id)

    st = builder_e2e_client.get(
        f"/api/v1/bots/{bot_id}/telegram/status",
        headers=auth_headers(access),
    )
    assert st.status_code == 200
    assert st.json()["channel_status"] == "channel_pending"

    tg_row = asyncio.run(fetch_telegram_config_row(live_db_url, monkeypatch, bot_id))
    assert tg_row is not None
    assert tg_row.provisioning_status == TELEGRAM_PROVISIONING_CHANNEL_PENDING
    assert tg_row.is_connected is False
    assert tg_row.bot_token_encrypted is None


def test_telegram_with_valid_token_active_and_connected_in_db(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "tg_token_ok")
    r = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "TG Token OK",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
            "telegram_bot_token": DEFAULT_VALID_TELEGRAM_TOKEN_FOR_TESTS,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    bot_id = uuid.UUID(body["id"])
    assert body["status"] == "active"
    assert body["primary_channel"] == "telegram"

    _assert_bot_api_matches_db(live_db_url=live_db_url, monkeypatch=monkeypatch, api_bot=body, bot_id=bot_id)

    tg_row = asyncio.run(fetch_telegram_config_row(live_db_url, monkeypatch, bot_id))
    assert tg_row is not None
    assert tg_row.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE
    assert tg_row.is_connected is True
    assert tg_row.bot_token_encrypted is not None


def test_invalid_telegram_token_does_not_leave_bot_row(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, owner_id = _register(builder_e2e_client, "tg_bad")
    assert asyncio.run(count_bots_for_owner(live_db_url, monkeypatch, owner_id)) == 0

    r = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "Should Not Persist",
            "niche_id": "education",
            "goal_type": "support",
            "initial_channel": "telegram",
            "telegram_bot_token": "123456789:AAH___BAD___token_xx",
        },
    )
    assert r.status_code == 422, r.text
    assert r.json().get("code") == "telegram_token_invalid"
    assert asyncio.run(count_bots_for_owner(live_db_url, monkeypatch, owner_id)) == 0


def test_telegram_channel_pending_cannot_patch_active_until_connected(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "tg_block_patch")
    create = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "Block Active",
            "niche_id": "services",
            "goal_type": "sales",
            "initial_channel": "telegram",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = uuid.UUID(create.json()["id"])

    patch = builder_e2e_client.patch(
        f"/api/v1/bots/{bot_id}",
        headers=auth_headers(access),
        json={"status": "active"},
    )
    assert patch.status_code == 422
    assert patch.json().get("code") == "bot_validation_error"

    row = asyncio.run(fetch_bot_row(live_db_url, monkeypatch, bot_id))
    assert row is not None
    assert row.status == "channel_pending"


def test_connect_telegram_after_pending_promotes_to_active_db(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "tg_connect")
    create = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "TG Connect Later",
            "niche_id": "dev_agency",
            "goal_type": "sales",
            "initial_channel": "telegram",
        },
    )
    assert create.status_code == 201, create.text
    bot_id = uuid.UUID(create.json()["id"])
    assert create.json()["status"] == "channel_pending"

    conn = builder_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=auth_headers(access),
        json={"bot_token": DEFAULT_VALID_TELEGRAM_TOKEN_FOR_TESTS},
    )
    assert conn.status_code == 200, conn.text

    final = builder_e2e_client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers(access))
    assert final.status_code == 200
    api_final = final.json()
    assert api_final["status"] == "active"

    _assert_bot_api_matches_db(
        live_db_url=live_db_url,
        monkeypatch=monkeypatch,
        api_bot=api_final,
        bot_id=bot_id,
    )


def test_both_channel_pending_then_token_connect_active(
    builder_e2e_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access, _ = _register(builder_e2e_client, "both_path")
    create = builder_e2e_client.post(
        "/api/v1/bots",
        headers=auth_headers(access),
        json={
            "name": "Both Channels",
            "niche_id": "education",
            "goal_type": "faq",
            "initial_channel": "both",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    bot_id = uuid.UUID(body["id"])
    assert body["status"] == "channel_pending"
    assert body["primary_channel"] == "both"

    _assert_bot_api_matches_db(live_db_url=live_db_url, monkeypatch=monkeypatch, api_bot=body, bot_id=bot_id)

    conn = builder_e2e_client.post(
        f"/api/v1/bots/{bot_id}/telegram/connect",
        headers=auth_headers(access),
        json={"bot_token": DEFAULT_VALID_TELEGRAM_TOKEN_FOR_TESTS},
    )
    assert conn.status_code == 200, conn.text

    api_after = builder_e2e_client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers(access)).json()
    assert api_after["status"] == "active"
    assert api_after["primary_channel"] == "both"

    row = asyncio.run(fetch_bot_row(live_db_url, monkeypatch, bot_id))
    assert row is not None
    assert row.status == "active"
