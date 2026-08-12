"""Unit tests for :class:`~app.services.bot_knowledge_file_service.BotKnowledgeFileService`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import Settings
from app.models.user import User
from app.services.bot_exceptions import BotNotFoundError
from app.services.bot_knowledge_file_service import BotKnowledgeFileService
from app.services.knowledge_file_exceptions import (
    KnowledgeFileStorageNotConfiguredError,
    KnowledgeFileValidationError,
)
from starlette.datastructures import Headers, UploadFile


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _user() -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    return u


def _settings_with_storage() -> Settings:
    return Settings(
        environment="local",
        object_storage_bucket="test-bucket",
        object_storage_access_key_id="ak",
        object_storage_secret_access_key="sk",
        object_storage_endpoint_url="http://localhost:9000",
    )


def _upload_pdf(filename: str = "guide.pdf") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(_pdf_bytes()),
        headers=Headers({"content-type": "application/pdf"}),
    )


def _file_repo_upload_defaults() -> AsyncMock:
    repo = AsyncMock()
    repo.count_knowledge_files_for_bot = AsyncMock(return_value=0)
    return repo


@pytest.mark.asyncio
async def test_upload_rejects_when_bot_not_found() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=False)
    file_repo = AsyncMock()
    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    with pytest.raises(BotNotFoundError):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), _upload_pdf())


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf_extension() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    up = UploadFile(
        filename="x.txt",
        file=BytesIO(_pdf_bytes()),
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(KnowledgeFileValidationError, match="\\.pdf"):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), up)


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_content_type() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    up = UploadFile(
        filename="x.pdf",
        file=BytesIO(_pdf_bytes()),
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(KnowledgeFileValidationError, match="PDF"):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), up)


@pytest.mark.asyncio
async def test_upload_accepts_octet_stream_when_magic_is_pdf() -> None:
    user = _user()
    bot_id = uuid.uuid4()
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    now = datetime.now(UTC)

    async def _create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=kwargs["file_id"],
            bot_id=kwargs["bot_id"],
            owner_id=kwargs["owner_id"],
            original_filename=kwargs["original_filename"],
            mime_type=kwargs["mime_type"],
            file_size_bytes=kwargs["file_size_bytes"],
            processing_status=kwargs["processing_status"],
            processing_error=None,
            page_count=None,
            uploaded_at=now,
            updated_at=now,
        )

    file_repo.create_knowledge_file = AsyncMock(side_effect=_create)
    file_repo.commit = AsyncMock()
    mock_storage = AsyncMock()
    mock_storage.upload_file = AsyncMock()
    up = UploadFile(
        filename="guide.pdf",
        file=BytesIO(_pdf_bytes()),
        headers=Headers({"content-type": "application/octet-stream"}),
    )
    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    with patch(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        return_value=mock_storage,
    ):
        await svc.upload_pdf_knowledge_file(user, bot_id, up)
    mock_storage.upload_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_rejects_pe_executable_prefix_even_with_pdf_substring() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    raw = b"MZ" + b"\x00" * 100 + b"%PDF-1.4 fake"
    up = UploadFile(
        filename="trick.pdf",
        file=BytesIO(raw),
        headers=Headers({"content-type": "application/pdf"}),
    )
    with pytest.raises(KnowledgeFileValidationError, match="not accepted"):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), up)


@pytest.mark.asyncio
async def test_upload_rejects_when_max_files_per_bot_reached() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    file_repo.count_knowledge_files_for_bot = AsyncMock(return_value=100)
    settings = _settings_with_storage()
    settings = settings.model_copy(update={"knowledge_max_files_per_bot": 100})
    svc = BotKnowledgeFileService(bot_repo, file_repo, settings)
    with pytest.raises(KnowledgeFileValidationError, match="Maximum number of knowledge files"):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), _upload_pdf())


@pytest.mark.asyncio
async def test_upload_rejects_when_storage_not_configured() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    settings = Settings(environment="local")
    svc = BotKnowledgeFileService(bot_repo, file_repo, settings)
    with pytest.raises(KnowledgeFileStorageNotConfiguredError):
        await svc.upload_pdf_knowledge_file(_user(), uuid.uuid4(), _upload_pdf())


@pytest.mark.asyncio
async def test_upload_persists_after_real_put_object() -> None:
    user = _user()
    bot_id = uuid.uuid4()
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = _file_repo_upload_defaults()
    now = datetime.now(UTC)

    async def _create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=kwargs["file_id"],
            bot_id=kwargs["bot_id"],
            owner_id=kwargs["owner_id"],
            original_filename=kwargs["original_filename"],
            mime_type=kwargs["mime_type"],
            file_size_bytes=kwargs["file_size_bytes"],
            processing_status=kwargs["processing_status"],
            processing_error=None,
            page_count=None,
            uploaded_at=now,
            updated_at=now,
        )

    file_repo.create_knowledge_file = AsyncMock(side_effect=_create)
    file_repo.commit = AsyncMock()

    mock_storage = AsyncMock()
    mock_storage.upload_file = AsyncMock()
    mock_storage.delete_file = AsyncMock()

    svc = BotKnowledgeFileService(bot_repo, file_repo, _settings_with_storage())
    with patch(
        "app.services.bot_knowledge_file_service.object_storage_from_settings",
        return_value=mock_storage,
    ):
        out = await svc.upload_pdf_knowledge_file(user, bot_id, _upload_pdf())

    mock_storage.upload_file.assert_awaited_once()
    kw = mock_storage.upload_file.await_args.kwargs
    assert kw["content_type"] == "application/pdf"
    assert kw["body"].startswith(b"%PDF")
    assert "v1/knowledge/owners/" in kw["key"]

    file_repo.create_knowledge_file.assert_awaited_once()
    file_repo.commit.assert_awaited_once()

    assert out.id == file_repo.create_knowledge_file.await_args.kwargs["file_id"]
    assert out.bot_id == bot_id
    assert out.owner_id == user.id
    assert out.mime_type == "application/pdf"
    assert out.processing_status == "uploaded"
    assert "storage_key" not in out.model_dump()


@pytest.mark.asyncio
async def test_list_raises_bot_not_found() -> None:
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=False)
    file_repo = AsyncMock()
    svc = BotKnowledgeFileService(bot_repo, file_repo, Settings(environment="local"))
    with pytest.raises(BotNotFoundError):
        await svc.list_knowledge_files_for_bot(_user(), uuid.uuid4())


@pytest.mark.asyncio
async def test_list_returns_items_and_total() -> None:
    user = _user()
    bot_id = uuid.uuid4()
    now = datetime.now(UTC)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        bot_id=bot_id,
        original_filename="a.pdf",
        mime_type="application/pdf",
        file_size_bytes=10,
        processing_status="uploaded",
        page_count=None,
        uploaded_at=now,
        updated_at=now,
    )
    bot_repo = AsyncMock()
    bot_repo.exists_for_owner = AsyncMock(return_value=True)
    file_repo = AsyncMock()
    file_repo.list_knowledge_files_for_bot = AsyncMock(return_value=[row])
    file_repo.count_knowledge_files_for_bot = AsyncMock(return_value=1)
    svc = BotKnowledgeFileService(bot_repo, file_repo, Settings(environment="local"))
    resp = await svc.list_knowledge_files_for_bot(user, bot_id)
    assert resp.total == 1
    assert len(resp.items) == 1
    assert resp.items[0].original_filename == "a.pdf"
