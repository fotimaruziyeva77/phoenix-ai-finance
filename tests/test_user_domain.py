"""User ORM metadata and Pydantic schemas (no DB required)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.models import User, UserRole
from app.models.base import Base
from app.models.enums import OAuthProvider
from app.schemas.user import (
    LoginRequest,
    MeResponse,
    OAuthCallbackRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from pydantic import ValidationError


def test_user_tables_registered_on_metadata():
    assert "users" in Base.metadata.tables
    assert "oauth_accounts" in Base.metadata.tables
    t_users = Base.metadata.tables["users"]
    t_oauth = Base.metadata.tables["oauth_accounts"]
    assert any(c.name == "email" for c in t_users.columns)
    assert "uq_users_email" in {c.name for c in t_users.constraints if c.name}
    assert "uq_oauth_provider_user" in {c.name for c in t_oauth.constraints if c.name}


def test_user_create_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.co", password="short", full_name=None)


def test_user_create_accepts_valid_payload():
    u = UserCreate(email="user@example.com", password="longenough", full_name="User")
    assert u.email == "user@example.com"


def test_me_response_from_user_like_object():
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid4(),
        email="me@example.com",
        full_name="Me",
        role=UserRole.customer_admin,
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )
    me = MeResponse.model_validate(row)
    assert me.email_verified_at is None
    assert me.plan_key is None


def test_token_and_refresh_schemas():
    TokenResponse(access_token="a", refresh_token="r", expires_in=3600)
    RefreshRequest(refresh_token="r")
    RefreshRequest(refresh_token=None)


def test_oauth_callback_request():
    OAuthCallbackRequest(provider=OAuthProvider.github, code="abc", state="s")


def test_login_request():
    LoginRequest(email="x@y.z", password="secret")


def test_user_read_roundtrip_from_orm_style():
    now = datetime.now(timezone.utc)
    uid = uuid4()
    row = SimpleNamespace(
        id=uid,
        email="read@example.com",
        full_name=None,
        role=UserRole.superadmin,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )
    data = UserRead.model_validate(row)
    assert data.id == uid
    assert data.role == UserRole.superadmin


def test_user_role_column_uses_expected_enum_values():
    assert UserRole.customer_admin.value == "customer_admin"
    col = User.__table__.c.role
    assert list(col.type.enums) == ["customer_admin", "superadmin"]
