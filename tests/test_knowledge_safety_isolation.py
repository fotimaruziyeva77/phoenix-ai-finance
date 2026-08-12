"""
Knowledge safety, tenant isolation, and upload validation.

* **Unit** (no DB): object-key layout and public schema guarantees.
* **Integration** (PostgreSQL): API denies non-owners; validation errors; responses omit ``storage_key``.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.integrations.storage.keys import knowledge_file_object_key
from app.main import app
from app.schemas.knowledge_file import KnowledgeFileListResponse, KnowledgeFilePublicRead
from fastapi.testclient import TestClient

from tests.db_alembic import run_alembic_upgrade_head
from tests.integration_db import integration_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- Unit: storage key strategy (no database) ---


def test_object_key_embeds_owner_bot_and_unique_file_id() -> None:
    owner = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    bot = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    fid = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    key = knowledge_file_object_key(
        owner_id=owner,
        bot_id=bot,
        file_id=fid,
        original_filename="manual.pdf",
    )
    assert key == (
        f"v1/knowledge/owners/{owner}/bots/{bot}/files/{fid}.pdf"
    )
    assert str(owner) in key and str(bot) in key and str(fid) in key


def test_object_key_is_distinct_per_bot_same_owner() -> None:
    owner = uuid.uuid4()
    bot_a = uuid.uuid4()
    bot_b = uuid.uuid4()
    fid = uuid.uuid4()
    ka = knowledge_file_object_key(owner_id=owner, bot_id=bot_a, file_id=fid, original_filename="x.pdf")
    kb = knowledge_file_object_key(owner_id=owner, bot_id=bot_b, file_id=fid, original_filename="x.pdf")
    assert ka != kb
    assert f"/bots/{bot_a}/" in ka
    assert f"/bots/{bot_b}/" in kb


def test_object_key_is_distinct_per_owner_same_file_id_value() -> None:
    """Same file UUID under another owner must not collide in object store layout."""
    o1 = uuid.uuid4()
    o2 = uuid.uuid4()
    bot = uuid.uuid4()
    fid = uuid.uuid4()
    k1 = knowledge_file_object_key(owner_id=o1, bot_id=bot, file_id=fid, original_filename="x.pdf")
    k2 = knowledge_file_object_key(owner_id=o2, bot_id=bot, file_id=fid, original_filename="x.pdf")
    assert k1 != k2


def test_object_key_only_appends_safe_pdf_suffix() -> None:
    owner, bot, fid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    base = knowledge_file_object_key(owner_id=owner, bot_id=bot, file_id=fid, original_filename=None)
    with_pdf = knowledge_file_object_key(
        owner_id=owner, bot_id=bot, file_id=fid, original_filename="doc.PDF",
    )
    assert with_pdf == base + ".pdf"
    # Traversal-like names must not inject path segments (only vetted suffix).
    weird = knowledge_file_object_key(
        owner_id=owner, bot_id=bot, file_id=fid, original_filename="../../../etc/passwd",
    )
    assert weird == base
    assert ".." not in weird


def test_public_upload_and_list_schemas_exclude_storage_key() -> None:
    """Enforce API contract: clients never receive internal object keys."""
    upload_sample = {
        "id": str(uuid.uuid4()),
        "bot_id": str(uuid.uuid4()),
        "original_filename": "a.pdf",
        "processing_status": "uploaded",
        "uploaded_at": "2020-01-01T00:00:00Z",
    }
    KnowledgeFilePublicRead.model_validate(
        {
            **upload_sample,
            "mime_type": "application/pdf",
            "file_size_bytes": 10,
            "owner_id": uuid.uuid4(),
            "updated_at": "2020-01-01T00:00:00Z",
        }
    )
    list_sample = {
        "items": [
            {
                "id": str(uuid.uuid4()),
                "bot_id": str(uuid.uuid4()),
                "original_filename": "a.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 10,
                "processing_status": "uploaded",
                "uploaded_at": "2020-01-01T00:00:00Z",
                "updated_at": "2020-01-01T00:00:00Z",
            }
        ],
        "total": 1,
    }
    parsed = KnowledgeFileListResponse.model_validate(list_sample)
    assert "storage_key" not in parsed.model_dump()


# --- Integration: HTTP + PostgreSQL (same prerequisites as knowledge_api) ---


def _integration_db_url() -> str | None:
    return integration_database_url()


_KNOWLEDGE_SAFETY_API_MARKS = [
    pytest.mark.integration,
    pytest.mark.knowledge_safety,
    pytest.mark.skipif(
        not integration_database_url(),
        reason=(
            "Set TEST_DATABASE_URL or host-reachable DATABASE_URL for knowledge safety API checks."
        ),
    ),
]


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
def safety_client(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
    mock_object_storage: AsyncMock,
) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "k-safe") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Safety"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _pdf_body() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _create_bot(client: TestClient, token: str, name: str = "Safe Bot") -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(token),
        json={"name": name, "niche_id": "education", "goal_type": "faq"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


class TestKnowledgeSafetyApiIntegration:
    """HTTP-level isolation and validation (requires PostgreSQL)."""

    pytestmark = _KNOWLEDGE_SAFETY_API_MARKS

    @pytest.fixture(scope="class", autouse=True)
    def _alembic_once(self) -> None:
        url = _integration_db_url()
        assert url is not None
        run_alembic_upgrade_head(database_url=url, project_root=PROJECT_ROOT)

    def test_safety_non_owner_cannot_upload_or_list(
        self,
        safety_client: TestClient,
        mock_object_storage: AsyncMock,
    ) -> None:
        owner_tok = _register_and_get_access(safety_client, _unique_email("own"))
        intruder_tok = _register_and_get_access(safety_client, _unique_email("intr"))
        bot_id = _create_bot(safety_client, owner_tok)

        up = safety_client.post(
            f"/api/v1/bots/{bot_id}/knowledge/files",
            headers=_auth_headers(intruder_tok),
            files={"file": ("secret.pdf", _pdf_body(), "application/pdf")},
        )
        assert up.status_code == 404, up.text
        assert up.json().get("error", {}).get("code") == "bot_not_found"
        mock_object_storage.upload_file.assert_not_called()

        ls = safety_client.get(
            f"/api/v1/bots/{bot_id}/knowledge/files",
            headers=_auth_headers(intruder_tok),
        )
        assert ls.status_code == 404, ls.text

    def test_safety_invalid_content_type_rejected(
        self,
        safety_client: TestClient,
        mock_object_storage: AsyncMock,
    ) -> None:
        tok = _register_and_get_access(safety_client, _unique_email("mime"))
        bot_id = _create_bot(safety_client, tok)
        r = safety_client.post(
            f"/api/v1/bots/{bot_id}/knowledge/files",
            headers=_auth_headers(tok),
            files={"file": ("x.pdf", _pdf_body(), "image/png")},
        )
        assert r.status_code == 422, r.text
        err = r.json().get("error", {})
        assert err.get("code") == "knowledge_file_validation_error"
        assert (err.get("details") or {}).get("reason") == "invalid_content_type"
        mock_object_storage.upload_file.assert_not_called()

    def test_safety_oversized_upload_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        live_db_url: str,
        mock_object_storage: AsyncMock,
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", live_db_url)
        monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
        monkeypatch.setenv("APP_RATE_LIMITING_ENABLED", "false")
        monkeypatch.setenv("APP_KNOWLEDGE_PDF_MAX_UPLOAD_BYTES", "1024")
        get_settings.cache_clear()
        asyncio.run(dispose_engine())
        try:
            with TestClient(app) as client:
                tok = _register_and_get_access(client, _unique_email("big"))
                bot_id = _create_bot(client, tok)
                big = _pdf_body() + b"x" * (1100 - len(_pdf_body()))
                r = client.post(
                    f"/api/v1/bots/{bot_id}/knowledge/files",
                    headers=_auth_headers(tok),
                    files={"file": ("big.pdf", big, "application/pdf")},
                )
        finally:
            asyncio.run(dispose_engine())
            get_settings.cache_clear()

        assert r.status_code == 422, r.text
        assert r.json().get("error", {}).get("code") == "knowledge_file_validation_error"
        assert (r.json().get("error", {}).get("details") or {}).get("reason") == "file_too_large"
        mock_object_storage.upload_file.assert_not_called()

    def test_safety_upload_and_list_json_never_include_storage_key(
        self,
        safety_client: TestClient,
        mock_object_storage: AsyncMock,
    ) -> None:
        tok = _register_and_get_access(safety_client, _unique_email("leak"))
        bot_id = _create_bot(safety_client, tok)
        up = safety_client.post(
            f"/api/v1/bots/{bot_id}/knowledge/files",
            headers=_auth_headers(tok),
            files={"file": ("handbook.pdf", _pdf_body(), "application/pdf")},
        )
        assert up.status_code == 201, up.text
        body = up.json()
        assert "storage_key" not in body
        KnowledgeFilePublicRead.model_validate(body)

        ls = safety_client.get(
            f"/api/v1/bots/{bot_id}/knowledge/files",
            headers=_auth_headers(tok),
        )
        assert ls.status_code == 200, ls.text
        payload = ls.json()
        assert "storage_key" not in payload
        KnowledgeFileListResponse.model_validate(payload)
        for item in payload.get("items", []):
            assert "storage_key" not in item
