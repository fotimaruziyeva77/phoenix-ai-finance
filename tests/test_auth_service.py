"""AuthService unit tests (mocked repository, no HTTP/DB)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.core.config import Settings, get_settings
from app.core.security import create_refresh_token
from app.lib.refresh_token_hash import hash_refresh_token
from app.models.enums import UserRole
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenExpiredError,
    RefreshTokenReuseDetectedError,
    RefreshTokenRevokedError,
)
from app.services.auth_service import AuthService
from app.services.refresh_session_constants import REVOKE_REASON_LOGOUT_ALL, REVOKE_REASON_ROTATED


@pytest.fixture
def auth_settings(monkeypatch, tmp_path) -> Settings:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JWT_SECRET_KEY", "unit_test_jwt_secret_key_min_32_chars!!")
    get_settings.cache_clear()
    yield Settings()
    get_settings.cache_clear()


@pytest.fixture
def refresh_repo() -> AsyncMock:
    r = AsyncMock()
    r.insert_session = AsyncMock()
    r.get_by_jti = AsyncMock(return_value=None)
    r.revoke_session = AsyncMock()
    r.revoke_family_active_sessions = AsyncMock()
    r.revoke_all_active_for_user = AsyncMock()
    r.list_active_sessions_for_user = AsyncMock(return_value=[])
    return r


def _user(
    *,
    email: str = "u@example.com",
    password_hash: str | None = "argon2$dummy",
    active: bool = True,
) -> User:
    uid = uuid.uuid4()
    now = datetime.now(UTC)
    return User(
        id=uid,
        email=email,
        password_hash=password_hash,
        full_name="U",
        role=UserRole.customer_admin,
        is_active=active,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )


def test_register_rejects_duplicate_email(auth_settings: Settings, refresh_repo: AsyncMock):
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=_user())
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(EmailAlreadyRegisteredError):
            await svc.register(
                UserCreate(email="u@example.com", password="password123", full_name=None)
            )

    asyncio.run(run())
    repo.create_email_password_user.assert_not_called()
    refresh_repo.insert_session.assert_not_called()


def test_login_rejects_unknown_user(auth_settings: Settings, refresh_repo: AsyncMock):
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(InvalidCredentialsError):
            await svc.login("missing@example.com", "password123")

    asyncio.run(run())


def test_login_rejects_oauth_only_user(auth_settings: Settings, refresh_repo: AsyncMock):
    repo = AsyncMock()
    u = _user(password_hash=None)
    repo.get_by_email = AsyncMock(return_value=u)
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(InvalidCredentialsError):
            await svc.login("u@example.com", "any")

    asyncio.run(run())


def test_login_rejects_inactive_user(auth_settings: Settings, monkeypatch, refresh_repo: AsyncMock):
    monkeypatch.setattr(
        "app.services.auth_service.verify_password", lambda raw, h: True
    )
    repo = AsyncMock()
    u = _user(active=False)
    repo.get_by_email = AsyncMock(return_value=u)
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(InactiveUserError):
            await svc.login("u@example.com", "password123")

    asyncio.run(run())


def test_register_creates_and_commits(auth_settings: Settings, monkeypatch, refresh_repo: AsyncMock):
    monkeypatch.setattr("app.services.auth_service.hash_password", lambda p: "hashed")

    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    new_u = _user(email="new@example.com", password_hash="hashed")
    repo.create_email_password_user = AsyncMock(return_value=new_u)
    repo.commit = AsyncMock()

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        out = await svc.register(
            UserCreate(email="new@example.com", password="password123", full_name="N")
        )
        assert out.user.email == "new@example.com"
        assert out.access_token
        assert out.refresh_token

    asyncio.run(run())
    repo.commit.assert_awaited_once()
    refresh_repo.insert_session.assert_awaited_once()


def test_login_success_returns_tokens(auth_settings: Settings, monkeypatch, refresh_repo: AsyncMock):
    monkeypatch.setattr(
        "app.services.auth_service.verify_password", lambda raw, h: raw == "ok"
    )

    repo = AsyncMock()
    u = _user(email="ok@example.com", password_hash="stored")
    repo.get_by_email = AsyncMock(return_value=u)
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        out = await svc.login("ok@example.com", "ok")
        assert out.user.email == "ok@example.com"
        assert out.access_token and out.refresh_token

    asyncio.run(run())


def _session_row(
    *,
    user: User,
    jti: str,
    raw_token: str,
    family_id: uuid.UUID,
    revoked_at: datetime | None = None,
    revoke_reason: str | None = None,
    expires_at: datetime | None = None,
) -> RefreshSession:
    now = datetime.now(UTC)
    return RefreshSession(
        id=uuid.uuid4(),
        user_id=user.id,
        family_id=family_id,
        jti=jti,
        token_hash=hash_refresh_token(raw_token),
        issued_at=now - timedelta(minutes=1),
        expires_at=expires_at or (now + timedelta(days=7)),
        rotated_from_jti=None,
        revoked_at=revoked_at,
        revoke_reason=revoke_reason,
        device_info=None,
        ip_address=None,
        user_agent=None,
    )


def test_refresh_rotates_commits(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    row = _session_row(user=user, jti=jti, raw_token=raw, family_id=family_id)

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=user)
    repo.commit = AsyncMock()
    repo.rollback = AsyncMock()
    refresh_repo.get_by_jti = AsyncMock(return_value=row)

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        out = await svc.refresh(raw)
        assert out.access_token and out.refresh_token
        assert out.refresh_token != raw

    asyncio.run(run())
    refresh_repo.revoke_session.assert_awaited_once()
    refresh_repo.insert_session.assert_awaited_once()
    repo.commit.assert_awaited_once()
    repo.rollback.assert_not_called()


def test_refresh_rollback_on_insert_failure(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    row = _session_row(user=user, jti=jti, raw_token=raw, family_id=family_id)

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=user)
    repo.commit = AsyncMock()
    repo.rollback = AsyncMock()
    refresh_repo.get_by_jti = AsyncMock(return_value=row)
    refresh_repo.insert_session = AsyncMock(side_effect=RuntimeError("db down"))

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(RuntimeError, match="db down"):
            await svc.refresh(raw)

    asyncio.run(run())
    repo.rollback.assert_awaited_once()
    repo.commit.assert_not_called()


def test_refresh_reuse_rotated_invalidates_family(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    now = datetime.now(UTC)
    row = _session_row(
        user=user,
        jti=jti,
        raw_token=raw,
        family_id=family_id,
        revoked_at=now,
        revoke_reason=REVOKE_REASON_ROTATED,
    )

    repo = AsyncMock()
    repo.commit = AsyncMock()
    refresh_repo.get_by_jti = AsyncMock(return_value=row)

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(RefreshTokenReuseDetectedError):
            await svc.refresh(raw)

    asyncio.run(run())
    refresh_repo.revoke_family_active_sessions.assert_awaited_once()
    repo.commit.assert_awaited_once()


def test_refresh_revoked_non_rotated_raises(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    now = datetime.now(UTC)
    row = _session_row(
        user=user,
        jti=jti,
        raw_token=raw,
        family_id=family_id,
        revoked_at=now,
        revoke_reason=REVOKE_REASON_LOGOUT_ALL,
    )
    refresh_repo.get_by_jti = AsyncMock(return_value=row)
    repo = AsyncMock()

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(RefreshTokenRevokedError):
            await svc.refresh(raw)

    asyncio.run(run())
    refresh_repo.revoke_family_active_sessions.assert_not_called()


def test_refresh_row_expired_raises(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    now = datetime.now(UTC)
    row = _session_row(
        user=user,
        jti=jti,
        raw_token=raw,
        family_id=family_id,
        expires_at=now - timedelta(seconds=1),
    )
    refresh_repo.get_by_jti = AsyncMock(return_value=row)
    repo = AsyncMock()

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(RefreshTokenExpiredError):
            await svc.refresh(raw)

    asyncio.run(run())


def test_refresh_hash_mismatch_raises(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    family_id = uuid.uuid4()
    jti = str(uuid.uuid4())
    raw = create_refresh_token(
        user.id,
        settings=auth_settings,
        jti=jti,
        family_id=family_id,
    )
    row = _session_row(
        user=user,
        jti=jti,
        raw_token=raw,
        family_id=family_id,
    )
    row.token_hash = "0" * 64
    refresh_repo.get_by_jti = AsyncMock(return_value=row)
    repo = AsyncMock()

    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        with pytest.raises(InvalidRefreshTokenError):
            await svc.refresh(raw)

    asyncio.run(run())


def test_logout_all_revokes_all(auth_settings: Settings, refresh_repo: AsyncMock):
    user = _user()
    repo = AsyncMock()
    repo.commit = AsyncMock()
    svc = AuthService(repo, refresh_repo, auth_settings)

    async def run() -> None:
        await svc.logout_all_refresh(user)

    asyncio.run(run())
    refresh_repo.revoke_all_active_for_user.assert_awaited_once()
    repo.commit.assert_awaited_once()
