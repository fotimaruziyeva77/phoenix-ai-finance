"""Superadmin overview HTTP smoke (dependency overrides; no database)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.api import deps as deps_mod
from app.main import create_app
from app.models.enums import UserRole
from app.schemas.platform_admin import AdminUserListResponse, AdminTenantInspectionResponse
from fastapi.testclient import TestClient


def test_admin_users_requires_superadmin() -> None:
    app = create_app()
    u = SimpleNamespace(id=uuid.uuid4(), role=UserRole.customer_admin)

    async def _fake_auth() -> SimpleNamespace:
        return u

    app.dependency_overrides[deps_mod.require_authenticated_user] = _fake_auth
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/admin/users")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


def test_admin_users_ok_with_superadmin_and_mock_service() -> None:
    app = create_app()
    sa = SimpleNamespace(id=uuid.uuid4(), role=UserRole.superadmin)

    async def _fake_auth() -> SimpleNamespace:
        return sa

    mock_svc = MagicMock()
    mock_svc.list_users = AsyncMock(
        return_value=AdminUserListResponse(items=[], total=0, limit=50, offset=0),
    )

    app.dependency_overrides[deps_mod.require_authenticated_user] = _fake_auth
    app.dependency_overrides[deps_mod.get_platform_admin_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/admin/users")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}
    mock_svc.list_users.assert_awaited_once()


def test_admin_tenant_inspection_requires_superadmin() -> None:
    app = create_app()
    u = SimpleNamespace(id=uuid.uuid4(), role=UserRole.customer_admin)

    async def _fake_auth() -> SimpleNamespace:
        return u

    app.dependency_overrides[deps_mod.require_authenticated_user] = _fake_auth
    try:
        with TestClient(app) as client:
            tid = str(uuid.uuid4())
            r = client.get(f"/api/v1/admin/tenants/{tid}/inspection")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403


def test_admin_tenant_inspection_ok_with_superadmin_and_mock_service() -> None:
    app = create_app()
    sa = SimpleNamespace(id=uuid.uuid4(), role=UserRole.superadmin)
    owner_id = uuid.uuid4()

    async def _fake_auth() -> SimpleNamespace:
        return sa

    mock_svc = MagicMock()
    mock_svc.inspect_tenant = AsyncMock(
        return_value=AdminTenantInspectionResponse.model_validate(
            {
                "tenant_user_id": str(owner_id),
                "summary": {
                    "id": str(owner_id),
                    "email": "t@example.com",
                    "full_name": "T",
                    "role": "customer_admin",
                    "is_active": True,
                    "is_verified": True,
                    "suspended_at": None,
                    "has_password": True,
                    "oauth_provider_count": 0,
                    "bot_count": 0,
                    "created_at": "2020-01-01T00:00:00Z",
                    "updated_at": "2020-01-01T00:00:00Z",
                    "suspension_reason": None,
                    "oauth_providers": [],
                },
                "bots": [],
                "channels": [],
                "lead_count": 0,
                "conversation_count": 0,
                "ai_usage": {
                    "period_start": "2020-01-01T00:00:00Z",
                    "period_end": "2020-01-02T00:00:00Z",
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_tokens": 0,
                },
                "ai_daily_usage": [],
                "recent_ai_failures": [],
            },
        ),
    )

    app.dependency_overrides[deps_mod.require_authenticated_user] = _fake_auth
    app.dependency_overrides[deps_mod.get_tenant_inspection_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            r = client.get(f"/api/v1/admin/tenants/{owner_id}/inspection")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["tenant_user_id"] == str(owner_id)
    mock_svc.inspect_tenant.assert_awaited_once()
