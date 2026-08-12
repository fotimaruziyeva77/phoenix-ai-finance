"""Unit tests for :mod:`app.core.rbac` (no HTTP, no database)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.api.deps import require_authenticated_user
from app.core.rbac import (
    PlatformCapability,
    is_customer_admin,
    is_superadmin,
    platform_capabilities_for,
    user_may,
)
from app.main import create_app
from app.models.enums import UserRole
from fastapi.testclient import TestClient


def _user(role: UserRole) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role)


def test_is_roles() -> None:
    ca = _user(UserRole.customer_admin)
    sa = _user(UserRole.superadmin)
    assert is_customer_admin(ca) is True
    assert is_superadmin(ca) is False
    assert is_customer_admin(sa) is False
    assert is_superadmin(sa) is True


def test_platform_capabilities_only_superadmin() -> None:
    ca = _user(UserRole.customer_admin)
    sa = _user(UserRole.superadmin)
    assert platform_capabilities_for(ca) == frozenset()
    assert PlatformCapability.LIST_TENANTS in platform_capabilities_for(sa)


def test_user_may() -> None:
    sa = _user(UserRole.superadmin)
    ca = _user(UserRole.customer_admin)
    assert user_may(sa, PlatformCapability.MODERATION_ACTIONS) is True
    assert user_may(ca, PlatformCapability.MODERATION_ACTIONS) is False


def test_admin_platform_session_401_without_authentication() -> None:
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/v1/admin/platform/session")
    assert r.status_code == 401


def test_admin_platform_session_403_for_customer_admin() -> None:
    app = create_app()
    u = SimpleNamespace(id=uuid.uuid4(), role=UserRole.customer_admin)

    async def _fake_auth() -> SimpleNamespace:
        return u

    app.dependency_overrides[require_authenticated_user] = _fake_auth
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/admin/platform/session")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403
    body = r.json()
    assert body.get("error", {}).get("message") == "Superadmin access required."


def test_admin_platform_session_200_for_superadmin() -> None:
    app = create_app()
    uid = uuid.uuid4()
    u = SimpleNamespace(id=uid, role=UserRole.superadmin)

    async def _fake_auth() -> SimpleNamespace:
        return u

    app.dependency_overrides[require_authenticated_user] = _fake_auth
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/admin/platform/session")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == str(uid)
    assert data["role"] == "superadmin"
