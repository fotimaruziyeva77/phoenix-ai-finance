"""
Auth API contract tests: OpenAPI shape + JSON samples validated with Pydantic.

Fails when documented response schemas drift from canonical models or error envelopes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
import pytest

from app.core.error_response import ErrorInfo, StandardErrorResponse
from app.models.enums import UserRole
from app.main import app
from app.schemas.auth import AuthSessionResponse, SessionStatusResponse
from app.schemas.auth_contract import ALL_DOCUMENTED_AUTH_ERROR_CODES
from app.schemas.user import MeResponse, TokenResponse, UserRead


def _openapi() -> dict[str, Any]:
    return app.openapi()


def _response_schema_for(path: str, method: str, status: str) -> dict[str, Any] | None:
    spec = _openapi()
    try:
        responses = spec["paths"][path][method]["responses"]
        entry = responses.get(status) or responses.get(str(status))
        if not entry:
            return None
        content = entry.get("content") or {}
        app_json = content.get("application/json") or {}
        return app_json.get("schema")
    except KeyError:
        return None


def test_openapi_register_documents_session_and_errors() -> None:
    schema = _response_schema_for("/api/v1/auth/register", "post", "201")
    assert schema is not None
    assert schema.get("$ref") or schema.get("properties")
    for code in ("409", "422", "429"):
        assert _response_schema_for("/api/v1/auth/register", "post", code) is not None


def test_openapi_login_documents_session_and_errors() -> None:
    assert _response_schema_for("/api/v1/auth/login", "post", "200") is not None
    for code in ("401", "403", "422", "429"):
        assert _response_schema_for("/api/v1/auth/login", "post", code) is not None


def test_openapi_refresh_documents_token_pair_and_errors() -> None:
    assert _response_schema_for("/api/v1/auth/refresh", "post", "200") is not None
    for code in ("401", "403", "422", "429"):
        assert _response_schema_for("/api/v1/auth/refresh", "post", code) is not None


def test_openapi_oauth_exchange_documents_session() -> None:
    assert _response_schema_for("/api/v1/auth/oauth/exchange", "post", "200") is not None
    assert _response_schema_for("/api/v1/auth/oauth/exchange", "post", "401") is not None


def test_openapi_google_callback_documents_redirect() -> None:
    spec = _openapi()
    r302 = spec["paths"]["/api/v1/auth/google/callback"]["get"]["responses"]["302"]
    assert "description" in r302
    assert "oauth_exchange_code" in r302["description"] or "oauth_error" in r302["description"]


def test_openapi_github_callback_documents_redirect() -> None:
    spec = _openapi()
    r302 = spec["paths"]["/api/v1/auth/github/callback"]["get"]["responses"]["302"]
    assert "description" in r302


def test_openapi_me_and_sessions_documented() -> None:
    assert _response_schema_for("/api/v1/auth/me", "get", "200") is not None
    assert _response_schema_for("/api/v1/auth/me", "get", "401") is not None
    assert _response_schema_for("/api/v1/auth/sessions", "get", "200") is not None


def test_openapi_standard_error_schema_requires_error_code_and_message() -> None:
    spec = _openapi()
    # Title may be prefixed (Pydantic v2); find StandardErrorResponse by suffix
    schemas = spec["components"]["schemas"]
    key = next(k for k in schemas if k.endswith("StandardErrorResponse"))
    std = schemas[key]
    err_prop = std["properties"]["error"]
    ref = err_prop["$ref"] if "$ref" in err_prop else err_prop["allOf"][0]["$ref"]
    err_name = ref.split("/")[-1]
    err = schemas[err_name]
    assert "code" in err["properties"]
    assert "message" in err["properties"]
    assert set(err.get("required", [])) >= {"code", "message"}


def test_auth_session_json_round_trip_bearer() -> None:
    uid = uuid.uuid4()
    now = datetime.now(UTC)
    user = UserRead(
        id=uid,
        email="a@example.com",
        full_name="A",
        role=UserRole.customer_admin,
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )
    raw = {
        "auth_transport": "bearer",
        "user": user.model_dump(mode="json"),
        "access_token": "at",
        "refresh_token": "rt",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    parsed = AuthSessionResponse.model_validate(raw)
    assert parsed.auth_transport == "bearer"
    assert parsed.user.email == "a@example.com"


def test_auth_session_json_round_trip_cookie_omitted_tokens() -> None:
    uid = uuid.uuid4()
    now = datetime.now(UTC)
    user = UserRead(
        id=uid,
        email="b@example.com",
        full_name=None,
        role=UserRole.customer_admin,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )
    raw = {
        "auth_transport": "cookie",
        "user": user.model_dump(mode="json"),
        "access_token": None,
        "refresh_token": None,
        "token_type": "Bearer",
        "expires_in": 900,
        "csrf_token": "csrf",
    }
    parsed = AuthSessionResponse.model_validate(raw)
    assert parsed.access_token is None
    assert parsed.csrf_token == "csrf"


def test_token_pair_json_round_trip() -> None:
    raw = {
        "auth_transport": "bearer",
        "access_token": "a",
        "refresh_token": "r",
        "token_type": "Bearer",
        "expires_in": 60,
    }
    TokenResponse.model_validate(raw)


def test_me_response_includes_optional_reserved_fields() -> None:
    uid = uuid.uuid4()
    now = datetime.now(UTC)
    m = MeResponse(
        id=uid,
        email="m@example.com",
        full_name=None,
        role=UserRole.customer_admin,
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
        email_verified_at=None,
        plan_key=None,
    )
    dumped = m.model_dump(mode="json")
    assert "email_verified_at" in dumped
    assert "plan_key" in dumped


def test_session_status_shape() -> None:
    SessionStatusResponse.model_validate({"authenticated": False})


def test_standard_error_envelope_parse() -> None:
    body = StandardErrorResponse(
        error=ErrorInfo(code="invalid_credentials", message="Invalid email or password", category="authentication")
    )
    StandardErrorResponse.model_validate(body.model_dump(mode="json"))


def test_documented_auth_error_codes_are_non_empty_strings() -> None:
    for c in ALL_DOCUMENTED_AUTH_ERROR_CODES:
        assert isinstance(c, str) and len(c) >= 2


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def test_refresh_without_token_returns_standard_error_with_stable_code(client) -> None:
    r = client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 422
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == "refresh_token_required"
    assert data["error"]["message"]
    assert data["error"].get("category") == "authentication"


def test_invalid_json_body_rejected_with_validation_error_code(client) -> None:
    r = client.post(
        "/api/v1/auth/register",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    data = r.json()
    assert data["error"]["code"] == "validation_error"
