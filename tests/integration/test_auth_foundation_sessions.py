"""
Email/password auth, refresh rotation, reuse detection, logout, and session listing.

Naming: ``test_*`` groups behavior (register, login, refresh, logout, sessions).
DB assertions use ``refresh_sessions`` revoke reasons (no mocked AuthService).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient

from app.core.config import get_settings

from tests.integration.auth_db import (
    REVOKE_REASON_FAMILY_INVALIDATED,
    REVOKE_REASON_LOGOUT,
    REVOKE_REASON_LOGOUT_ALL,
    REVOKE_REASON_ROTATED,
    refresh_rows_by_jtis,
)
from tests.integration.auth_setup import (
    assert_error_envelope,
    login_user,
    refresh_jti,
    register_user,
    unique_email,
)


def test_register_returns_tokens_and_profile(auth_http_client: TestClient) -> None:
    email = unique_email("reg")
    data = register_user(auth_http_client, email)
    assert data["user"]["email"] == email
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] >= 60
    assert data["auth_transport"] == "bearer"


def test_register_duplicate_email_returns_409(auth_http_client: TestClient) -> None:
    email = unique_email("dup")
    register_user(auth_http_client, email)
    r = auth_http_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "otherpass123", "full_name": "X"},
    )
    assert_error_envelope(r, status_code=409, code="email_already_registered")


def test_login_success_returns_fresh_session(auth_http_client: TestClient) -> None:
    email = unique_email("login")
    password = "mySecurePass99"
    register_user(auth_http_client, email, password)
    data = login_user(auth_http_client, email, password)
    assert data["user"]["email"] == email
    assert data["access_token"] and data["refresh_token"]


def test_login_invalid_password_returns_401(auth_http_client: TestClient) -> None:
    email = unique_email("badpw")
    register_user(auth_http_client, email, "correctHorseBattery99")
    r = auth_http_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong_password_here"},
    )
    body = assert_error_envelope(r, status_code=401, code="invalid_credentials")
    assert body["error"].get("category") == "authentication"


def test_refresh_rotates_tokens_and_marks_old_row_rotated(
    auth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("rotate")
    reg = register_user(auth_http_client, email)
    old_rt = reg["refresh_token"]
    old_jti = refresh_jti(old_rt, get_settings())
    r = auth_http_client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"] != reg["access_token"]
    assert body["refresh_token"] != old_rt
    new_jti = refresh_jti(body["refresh_token"], get_settings())
    rows = refresh_rows_by_jtis([old_jti, new_jti], live_db_url, monkeypatch)
    by_jti = {row.jti: row for row in rows}
    assert by_jti[old_jti].revoke_reason == REVOKE_REASON_ROTATED
    assert by_jti[old_jti].revoked_at is not None
    assert by_jti[new_jti].revoked_at is None


def test_refresh_reuse_invalidates_family_in_database(
    auth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("reuse")
    reg = register_user(auth_http_client, email)
    old_rt = reg["refresh_token"]
    r1 = auth_http_client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert r1.status_code == 200, r1.text
    new_rt = r1.json()["refresh_token"]
    new_jti = refresh_jti(new_rt, get_settings())
    r2 = auth_http_client.post("/api/v1/auth/refresh", json={"refresh_token": old_rt})
    assert_error_envelope(r2, status_code=401, code="refresh_token_reuse_detected")
    rows = refresh_rows_by_jtis([new_jti], live_db_url, monkeypatch)
    assert len(rows) == 1
    assert rows[0].revoke_reason == REVOKE_REASON_FAMILY_INVALIDATED
    assert rows[0].revoked_at is not None


def test_logout_current_revokes_row_in_database(
    auth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("logout_cur")
    reg = register_user(auth_http_client, email)
    jti = refresh_jti(reg["refresh_token"], get_settings())
    r = auth_http_client.post(
        "/api/v1/auth/logout-current",
        json={"refresh_token": reg["refresh_token"]},
    )
    assert r.status_code == 204, r.text
    rows = refresh_rows_by_jtis([jti], live_db_url, monkeypatch)
    assert rows[0].revoke_reason == REVOKE_REASON_LOGOUT
    assert rows[0].revoked_at is not None
    ref = auth_http_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": reg["refresh_token"]},
    )
    assert_error_envelope(ref, status_code=401, code="refresh_token_revoked")


def test_logout_all_revokes_all_active_sessions(
    auth_http_client: TestClient,
    live_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = unique_email("logout_all")
    password = "p4ssword!!"
    reg = register_user(auth_http_client, email, password)
    login2 = auth_http_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login2.status_code == 200, login2.text
    jti_a = refresh_jti(reg["refresh_token"], get_settings())
    jti_b = refresh_jti(login2.json()["refresh_token"], get_settings())
    r = auth_http_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert r.status_code == 204, r.text
    rows = refresh_rows_by_jtis([jti_a, jti_b], live_db_url, monkeypatch)
    assert {row.revoke_reason for row in rows} == {REVOKE_REASON_LOGOUT_ALL}
    assert all(row.revoked_at is not None for row in rows)


def test_list_sessions_matches_active_refresh_rows(auth_http_client: TestClient) -> None:
    email = unique_email("sessions")
    reg = register_user(auth_http_client, email)
    r = auth_http_client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {reg['access_token']}"},
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert "items" in payload
    assert len(payload["items"]) >= 1
    jtis = {item["jti"] for item in payload["items"]}
    assert refresh_jti(reg["refresh_token"], get_settings()) in jtis
