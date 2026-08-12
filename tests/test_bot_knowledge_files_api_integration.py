"""
API integration tests for ``POST/GET /api/v1/bots/{bot_id}/knowledge/files``.

Requires PostgreSQL + Alembic head. Object storage is mocked (upload still exercised).
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import asyncpg
import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from fastapi.testclient import TestClient

from tests.db_alembic import run_alembic_upgrade_head
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_INTEGRATION_KEY = "x" * 32


def _integration_db_url() -> str | None:
    return integration_database_url()


pytestmark = [
    pytest.mark.integration,
    pytest.mark.knowledge_api,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason=(
            "Set TEST_DATABASE_URL (recommended) or host-reachable DATABASE_URL "
            "(not @postgres: — use 127.0.0.1 when testing from the host)."
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _alembic_for_knowledge_api() -> None:
    url = _integration_db_url()
    assert url is not None
    run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def mock_object_storage(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    storage = AsyncMock()
    storage.upload_file = AsyncMock()
    storage.delete_file = AsyncMock()
    monkeypatch.setattr(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        lambda *_a, **_kw: storage,
    )
    return storage


@pytest.fixture
def kf_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    mock_object_storage: AsyncMock,
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "kf-api") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "KF API"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _pdf_body() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _create_bot(client: TestClient, token: str, name: str = "KF Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(token),
        json={"name": name, "niche_id": "education", "goal_type": "faq"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _asyncpg_dsn(async_pg_url: str) -> str:
    if "+asyncpg" in async_pg_url:
        return async_pg_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return async_pg_url


async def _fetch_knowledge_file_row_asyncpg(db_url: str, file_id: uuid.UUID) -> asyncpg.Record | None:
    conn = await asyncpg.connect(dsn=_asyncpg_dsn(db_url))
    try:
        return await conn.fetchrow(
            "SELECT storage_key, processing_status, file_size_bytes FROM knowledge_files WHERE id = $1",
            file_id,
        )
    finally:
        await conn.close()


def test_knowledge_upload_unauthorized_returns_401(kf_client: TestClient) -> None:
    r = kf_client.post(
        f"/api/v1/bots/{uuid.uuid4()}/knowledge/files",
        files={"file": ("x.pdf", _pdf_body(), "application/pdf")},
    )
    assert r.status_code == 401


def test_knowledge_upload_non_owner_returns_404(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    owner_tok = _register_and_get_access(kf_client, _unique_email("owner404"))
    other_tok = _register_and_get_access(kf_client, _unique_email("other404"))
    bot_id = _create_bot(kf_client, owner_tok)

    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(other_tok),
        files={"file": ("handbook.pdf", _pdf_body(), "application/pdf")},
    )
    assert r.status_code == 404, r.text
    err = r.json().get("error", {})
    assert err.get("code") == "bot_not_found"
    mock_object_storage.upload_file.assert_not_called()


def test_knowledge_upload_owner_success_metadata_and_storage(
    kf_client: TestClient,
    live_db_url: str,
    mock_object_storage: AsyncMock,
) -> None:
    token = _register_and_get_access(kf_client, _unique_email("ownerok"))
    bot_id = _create_bot(kf_client, token)

    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("handbook.pdf", _pdf_body(), "application/pdf")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["bot_id"] == bot_id
    assert body["original_filename"] == "handbook.pdf"
    assert body["mime_type"] == "application/pdf"
    assert body["processing_status"] == "uploaded"
    assert body["file_size_bytes"] == len(_pdf_body())
    assert "storage_key" not in body

    mock_object_storage.upload_file.assert_awaited_once()
    uk = mock_object_storage.upload_file.await_args.kwargs
    assert uk["content_type"] == "application/pdf"
    assert uk["body"] == _pdf_body()
    assert uk["key"].startswith("v1/knowledge/owners/")

    fid = uuid.UUID(body["id"])
    row = asyncio.run(_fetch_knowledge_file_row_asyncpg(live_db_url, fid))
    assert row is not None
    assert row["storage_key"] == uk["key"]
    assert row["processing_status"] == "uploaded"
    assert row["file_size_bytes"] == len(_pdf_body())


def test_knowledge_upload_rejects_wrong_extension(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    token = _register_and_get_access(kf_client, _unique_email("badext"))
    bot_id = _create_bot(kf_client, token)

    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("notes.txt", _pdf_body(), "application/pdf")},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("error", {}).get("code") == "knowledge_file_validation_error"
    mock_object_storage.upload_file.assert_not_called()


def test_knowledge_upload_rejects_invalid_pdf_magic(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    token = _register_and_get_access(kf_client, _unique_email("badmagic"))
    bot_id = _create_bot(kf_client, token)

    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("x.pdf", b"NOTPDF content", "application/pdf")},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("error", {}).get("code") == "knowledge_file_validation_error"
    assert (r.json().get("error", {}).get("details") or {}).get("reason") == "invalid_pdf_magic"
    mock_object_storage.upload_file.assert_not_called()


def test_knowledge_upload_rejects_wrong_content_type(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    token = _register_and_get_access(kf_client, _unique_email("badmime"))
    bot_id = _create_bot(kf_client, token)

    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("ok.pdf", _pdf_body(), "image/png")},
    )
    assert r.status_code == 422, r.text
    assert r.json().get("error", {}).get("code") == "knowledge_file_validation_error"
    details = r.json().get("error", {}).get("details")
    assert isinstance(details, dict)
    assert details.get("reason") == "invalid_content_type"
    mock_object_storage.upload_file.assert_not_called()


def test_knowledge_upload_accepts_octet_stream_when_pdf_magic_valid(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    token = _register_and_get_access(kf_client, _unique_email("octetok"))
    bot_id = _create_bot(kf_client, token)
    r = kf_client.post(
        f"/api/v1/bots/{bot_id}/knowledge/files",
        headers=_auth_headers(token),
        files={"file": ("guide.pdf", _pdf_body(), "application/octet-stream")},
    )
    assert r.status_code == 201, r.text
    mock_object_storage.upload_file.assert_awaited_once()


def test_knowledge_upload_rejects_oversized_file(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    mock_object_storage: AsyncMock,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("APP_KNOWLEDGE_PDF_MAX_UPLOAD_BYTES", "1024")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    try:
        with TestClient(app) as client:
            token = _register_and_get_access(client, _unique_email("huge"))
            bot_id = _create_bot(client, token)
            big = _pdf_body() + b"x" * (1100 - len(_pdf_body()))
            r = client.post(
                f"/api/v1/bots/{bot_id}/knowledge/files",
                headers=_auth_headers(token),
                files={"file": ("big.pdf", big, "application/pdf")},
            )
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()

    assert r.status_code == 422, r.text
    assert r.json().get("error", {}).get("code") == "knowledge_file_validation_error"
    det = r.json().get("error", {}).get("details") or {}
    assert det.get("reason") == "file_too_large"
    mock_object_storage.upload_file.assert_not_called()


def test_knowledge_list_scoped_per_bot_and_owner(
    kf_client: TestClient,
    mock_object_storage: AsyncMock,
) -> None:
    owner_tok = _register_and_get_access(kf_client, _unique_email("listowner"))
    other_tok = _register_and_get_access(kf_client, _unique_email("listother"))
    bot_a = _create_bot(kf_client, owner_tok, "Bot A")
    bot_b = _create_bot(kf_client, owner_tok, "Bot B")
    _create_bot(kf_client, other_tok, "Foreign Bot")

    up1 = kf_client.post(
        f"/api/v1/bots/{bot_a}/knowledge/files",
        headers=_auth_headers(owner_tok),
        files={"file": ("a.pdf", _pdf_body(), "application/pdf")},
    )
    assert up1.status_code == 201, up1.text
    up2 = kf_client.post(
        f"/api/v1/bots/{bot_b}/knowledge/files",
        headers=_auth_headers(owner_tok),
        files={"file": ("b.pdf", _pdf_body(), "application/pdf")},
    )
    assert up2.status_code == 201, up2.text

    la = kf_client.get(f"/api/v1/bots/{bot_a}/knowledge/files", headers=_auth_headers(owner_tok))
    assert la.status_code == 200, la.text
    ja = la.json()
    assert ja["total"] == 1
    assert len(ja["items"]) == 1
    assert ja["items"][0]["original_filename"] == "a.pdf"

    lb = kf_client.get(f"/api/v1/bots/{bot_b}/knowledge/files", headers=_auth_headers(owner_tok))
    assert lb.status_code == 200, lb.text
    jb = lb.json()
    assert jb["total"] == 1
    assert jb["items"][0]["original_filename"] == "b.pdf"

    forbidden = kf_client.get(f"/api/v1/bots/{bot_a}/knowledge/files", headers=_auth_headers(other_tok))
    assert forbidden.status_code == 404
