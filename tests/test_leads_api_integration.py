"""
Leads API integration tests (authenticated, owner-scoped list / detail / status patch).

Uses ``httpx.AsyncClient`` + ``ASGITransport`` so DB seeding and request handling share one
event loop (``asyncio.run`` + sync ``TestClient`` would bind asyncpg to the wrong loop).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.main import app
from app.models.bot import Bot
from app.models.lead import Lead
from app.models.user import User
from sqlalchemy import select

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
def _alembic_for_leads_api() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
async def leads_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    get_settings.cache_clear()
    await dispose_engine()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await dispose_engine()
    get_settings.cache_clear()


def _unique_email(prefix: str = "leads-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


async def _register_and_get_access(client: httpx.AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Leads API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _assert_clean_json_error(
    response: httpx.Response,
    *,
    status_code: int,
    code: str,
    category: str | None = None,
) -> None:
    assert response.status_code == status_code, response.text
    payload = response.json()
    assert "error" in payload, payload
    err = payload["error"]
    assert isinstance(err.get("code"), str) and err["code"] == code
    assert isinstance(err.get("message"), str) and len(err["message"]) > 0
    if category is not None:
        assert err.get("category") == category


async def _create_lead_for_owner_email(owner_email: str) -> uuid.UUID:
    sm = get_session_maker()
    async with sm() as session:
        owner = (
            await session.execute(select(User).where(User.email == owner_email).limit(1))
        ).scalar_one()
        bot = Bot(
            owner_id=owner.id,
            name="Leads API Bot",
            niche_id="education",
            goal_type="sales",
            status="active",
        )
        session.add(bot)
        await session.flush()
        lead = Lead(
            bot_id=bot.id,
            owner_id=owner.id,
            niche_id="education",
            lead_temperature="warm",
        )
        session.add(lead)
        await session.commit()
        return lead.id


async def test_leads_api_owner_list_fetch_update_filters_and_errors(
    leads_client: httpx.AsyncClient,
) -> None:
    """
    Covers: owner list/detail/patch, non-owner denied, filters (status, niche, temperature),
    and stable error envelopes (404/409/422/401).
    """
    owner_mail = _unique_email("owner")
    owner_access = await _register_and_get_access(leads_client, owner_mail)
    other_access = await _register_and_get_access(leads_client, _unique_email("other"))

    lead_id = await _create_lead_for_owner_email(owner_mail)

    # 1) Owner can list leads
    list_resp = await leads_client.get(
        "/api/v1/leads",
        headers=_auth_headers(owner_access),
    )
    assert list_resp.status_code == 200, list_resp.text
    body = list_resp.json()
    assert "items" in body and "total" in body
    assert body["total"] >= 1
    ids = {item["id"] for item in body["items"]}
    assert str(lead_id) in ids

    # 5) Filters — status (lead seeded as ``new``)
    status_filtered = await leads_client.get(
        "/api/v1/leads",
        headers=_auth_headers(owner_access),
        params={"status": "new"},
    )
    assert status_filtered.status_code == 200
    assert str(lead_id) in {x["id"] for x in status_filtered.json()["items"]}
    won_only = await leads_client.get(
        "/api/v1/leads",
        headers=_auth_headers(owner_access),
        params={"status": "won"},
    )
    assert won_only.json()["items"] == []

    # 5) Filters — niche and temperature
    niche_filtered = await leads_client.get(
        "/api/v1/leads",
        headers=_auth_headers(owner_access),
        params={"niche": "other-niche"},
    )
    assert niche_filtered.status_code == 200
    assert niche_filtered.json()["items"] == []

    temp_filtered = await leads_client.get(
        "/api/v1/leads",
        headers=_auth_headers(owner_access),
        params={"temperature": "warm"},
    )
    assert temp_filtered.status_code == 200
    assert str(lead_id) in {x["id"] for x in temp_filtered.json()["items"]}

    # 2) Owner can fetch lead detail
    detail = await leads_client.get(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(owner_access),
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "new"

    # 4) Non-owner cannot read another user's lead (404, not 403 — no id leak)
    alien_get = await leads_client.get(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(other_access),
    )
    _assert_clean_json_error(alien_get, status_code=404, code="lead_not_found", category="leads")

    # 3) Owner can update status (and notes in same payload)
    patch = await leads_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted", "notes": "Called once."},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["status"] == "contacted"
    assert patch.json()["notes"] == "Called once."

    # 3b) Updated status (and notes) persist on subsequent GET detail
    verify_detail = await leads_client.get(
        f"/api/v1/leads/{lead_id}",
        headers=_auth_headers(owner_access),
    )
    assert verify_detail.status_code == 200, verify_detail.text
    verified = verify_detail.json()
    assert verified["status"] == "contacted"
    assert verified["notes"] == "Called once."

    # 4) Non-owner cannot PATCH another user's lead
    alien_patch = await leads_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(other_access),
        json={"status": "qualified"},
    )
    _assert_clean_json_error(alien_patch, status_code=404, code="lead_not_found", category="leads")

    # Terminal transition then blocked change — 409 clean envelope
    assert (
        await leads_client.patch(
            f"/api/v1/leads/{lead_id}/status",
            headers=_auth_headers(owner_access),
            json={"status": "won"},
        )
    ).status_code == 200

    blocked = await leads_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={"status": "contacted"},
    )
    _assert_clean_json_error(
        blocked,
        status_code=409,
        code="lead_invalid_status_transition",
        category="leads",
    )

    # 6) Validation errors — standard shape (no stack traces in body)
    missing_status = await leads_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        headers=_auth_headers(owner_access),
        json={},
    )
    _assert_clean_json_error(missing_status, status_code=422, code="validation_error")
    assert "details" in missing_status.json()["error"]

    unknown_lead = await leads_client.get(
        f"/api/v1/leads/{uuid.uuid4()}",
        headers=_auth_headers(owner_access),
    )
    _assert_clean_json_error(unknown_lead, status_code=404, code="lead_not_found", category="leads")


async def test_leads_api_requires_auth(leads_client: httpx.AsyncClient) -> None:
    r = await leads_client.get("/api/v1/leads")
    _assert_clean_json_error(r, status_code=401, code="not_authenticated", category="authentication")


async def test_lead_detail_and_status_patch_require_auth(
    leads_client: httpx.AsyncClient,
) -> None:
    """Anonymous clients cannot read or update a specific lead."""
    owner_mail = _unique_email("detail-auth")
    owner_access = await _register_and_get_access(leads_client, owner_mail)
    lead_id = await _create_lead_for_owner_email(owner_mail)

    get_anon = await leads_client.get(f"/api/v1/leads/{lead_id}")
    _assert_clean_json_error(
        get_anon,
        status_code=401,
        code="not_authenticated",
        category="authentication",
    )

    patch_anon = await leads_client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "contacted", "lead_temperature": None, "notes": None},
    )
    _assert_clean_json_error(
        patch_anon,
        status_code=401,
        code="not_authenticated",
        category="authentication",
    )

    # Owner still reaches the resource after anonymous attempts
    ok = await leads_client.get(f"/api/v1/leads/{lead_id}", headers=_auth_headers(owner_access))
    assert ok.status_code == 200, ok.text
