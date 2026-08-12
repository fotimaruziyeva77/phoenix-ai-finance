"""
Bootstrap vs chat: same domain allowlist policy (integration, PostgreSQL).

Verifies ``enforce_public_widget_origin_and_enabled`` outcomes match across GET bootstrap
and POST chat for the same widget key and headers.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.ai_providers.base import AIProvider
from app.ai_providers.types import GenerateParams, NormalizedAIResult, TokenUsage
from app.core.config import get_settings
from app.core.db import dispose_engine
from app.main import app
from fastapi.testclient import TestClient

from tests.integration_db import integration_database_url
from tests.public_widget_paths import public_widget_bootstrap_path, public_widget_chat_path

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
def _alembic_for_domain_enforcement() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)


@pytest.fixture
def live_db_url() -> str:
    u = _integration_db_url()
    assert u is not None
    return u


@pytest.fixture
def domain_policy_client(monkeypatch: pytest.MonkeyPatch, live_db_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    asyncio.run(dispose_engine())
    get_settings.cache_clear()


def _unique_email(prefix: str = "domain-parity") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"


def _register_and_get_access(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Domain Parity"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["access_token"])


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _create_bot(client: TestClient, access_token: str, *, name: str) -> str:
    r = client.post(
        "/api/v1/bots",
        headers=_auth_headers(access_token),
        json={"name": name, "niche_id": "education", "goal_type": "support"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


class _FakeProviderOk(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-domain-test"

    async def generate_response(self, params: GenerateParams) -> NormalizedAIResult:
        return NormalizedAIResult(
            success=True,
            provider_name="gemini",
            text="ok",
            model_name=params.model,
            tokens=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )

    def parse_usage(self, raw):
        return None

    def normalize_error(self, exc: BaseException) -> tuple[str | None, str]:
        return ("x", "y")

    async def aclose(self) -> None:
        pass


def _patch_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.ai_service.resolve_ai_provider",
        lambda _settings, _provider_id=None: _FakeProviderOk(),
    )


def _widget_with_allowlist(
    client: TestClient,
    *,
    domains: list[str],
) -> tuple[str, str]:
    access = _register_and_get_access(client, _unique_email())
    bot_id = _create_bot(client, access, name="Domain Policy Bot")
    w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
    assert w.status_code == 200, w.text
    public_key = str(w.json()["public_widget_key"])
    p = client.patch(
        f"/api/v1/bots/{bot_id}/widget",
        headers=_auth_headers(access),
        json={"allowed_domains_json": domains},
    )
    assert p.status_code == 200, p.text
    return public_key, bot_id


def _assert_origin_forbidden(resp) -> None:
    assert resp.status_code == 403, resp.text
    err = resp.json().get("error", {})
    assert err.get("code") == "widget_origin_forbidden"
    assert err.get("message") == "This widget cannot be loaded from this site."


def test_disallowed_and_allowed_origin_parity_bootstrap_and_chat(
    domain_policy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same key: bad Origin → 403 for both; good Origin → 200 for both."""
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_with_allowlist(domain_policy_client, domains=["parity.embed.test"])
    good_headers = {"Origin": "https://parity.embed.test"}
    bad_headers = {"Origin": "https://evil.other.test"}

    b_bad = domain_policy_client.get(public_widget_bootstrap_path(public_key), headers=bad_headers)
    _assert_origin_forbidden(b_bad)
    c_bad = domain_policy_client.post(
        public_widget_chat_path(public_key),
        headers=bad_headers,
        json={"message": "hi"},
    )
    _assert_origin_forbidden(c_bad)

    b_ok = domain_policy_client.get(public_widget_bootstrap_path(public_key), headers=good_headers)
    assert b_ok.status_code == 200, b_ok.text
    assert b_ok.json()["bot_display_name"] == "Domain Policy Bot"

    c_ok = domain_policy_client.post(
        public_widget_chat_path(public_key),
        headers=good_headers,
        json={"message": "hi"},
    )
    assert c_ok.status_code == 200, c_ok.text
    assert c_ok.json()["assistant_text"] == "ok"


def test_loopback_localhost_list_allows_127_bootstrap_and_chat(
    domain_policy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default APP_PUBLIC_WIDGET_ORIGIN_LOOPBACK_EQUIVALENT: 127.0.0.1 matches localhost entry."""
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_with_allowlist(domain_policy_client, domains=["localhost"])
    headers = {"Origin": "http://127.0.0.1:5173"}

    b = domain_policy_client.get(public_widget_bootstrap_path(public_key), headers=headers)
    assert b.status_code == 200, b.text
    c = domain_policy_client.post(public_widget_chat_path(public_key), headers=headers, json={"message": "x"})
    assert c.status_code == 200, c.text


def test_loopback_equivalence_disabled_blocks_127_when_only_localhost_listed(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ORIGIN_LOOPBACK_EQUIVALENT", "false")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    _patch_fake_provider(monkeypatch)
    try:
        with TestClient(app) as client:
            public_key, _ = _widget_with_allowlist(client, domains=["localhost"])
            headers = {"Origin": "http://127.0.0.1:5173"}
            b = client.get(public_widget_bootstrap_path(public_key), headers=headers)
            _assert_origin_forbidden(b)
            c = client.post(public_widget_chat_path(public_key), headers=headers, json={"message": "x"})
            _assert_origin_forbidden(c)
    finally:
        asyncio.run(dispose_engine())
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "origin_value",
    [
        "https://not-on-list.example",
        "not-a-valid-url-but-hostname",
        "%%%",  # garbage still parsed as a label-like token by our normalizer
    ],
)
def test_malformed_or_foreign_origin_denied_without_5xx_bootstrap_and_chat(
    domain_policy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    origin_value: str,
) -> None:
    """Non-matching origins must return 403 policy, never server errors."""
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_with_allowlist(domain_policy_client, domains=["only.allowed.test"])
    headers = {"Origin": origin_value}

    b = domain_policy_client.get(public_widget_bootstrap_path(public_key), headers=headers)
    assert b.status_code == 403, b.text
    assert b.status_code < 500
    _assert_origin_forbidden(b)

    c = domain_policy_client.post(public_widget_chat_path(public_key), headers=headers, json={"message": "hi"})
    assert c.status_code == 403, c.text
    assert c.status_code < 500
    _assert_origin_forbidden(c)


def test_wildcard_allowlist_parity_bootstrap_and_chat(
    domain_policy_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_provider(monkeypatch)
    public_key, _ = _widget_with_allowlist(domain_policy_client, domains=["*.wild.parity.test"])

    apex = domain_policy_client.get(
        public_widget_bootstrap_path(public_key),
        headers={"Origin": "https://wild.parity.test"},
    )
    _assert_origin_forbidden(apex)

    sub_ok = domain_policy_client.get(
        public_widget_bootstrap_path(public_key),
        headers={"Origin": "https://app.wild.parity.test"},
    )
    assert sub_ok.status_code == 200, sub_ok.text

    c = domain_policy_client.post(
        public_widget_chat_path(public_key),
        headers={"Origin": "https://app.wild.parity.test"},
        json={"message": "hi"},
    )
    assert c.status_code == 200, c.text


def test_empty_allowlist_parity_bootstrap_and_chat_when_force_deny_empty(
    monkeypatch: pytest.MonkeyPatch,
    live_db_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", live_db_url)
    monkeypatch.setenv("JWT_SECRET_KEY", JWT_INTEGRATION_KEY)
    monkeypatch.setenv("GEMINI_API_KEY", "integration-placeholder-key")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST", "true")
    get_settings.cache_clear()
    asyncio.run(dispose_engine())
    _patch_fake_provider(monkeypatch)
    try:
        with TestClient(app) as client:
            access = _register_and_get_access(client, _unique_email("empty-deny"))
            bot_id = _create_bot(client, access, name="Empty Deny Bot")
            w = client.get(f"/api/v1/bots/{bot_id}/widget", headers=_auth_headers(access))
            assert w.status_code == 200, w.text
            public_key = str(w.json()["public_widget_key"])

            b = client.get(
                public_widget_bootstrap_path(public_key),
                headers={"Origin": "https://any.test"},
            )
            _assert_origin_forbidden(b)
            c = client.post(
                public_widget_chat_path(public_key),
                headers={"Origin": "https://any.test"},
                json={"message": "hi"},
            )
            _assert_origin_forbidden(c)
    finally:
        asyncio.run(dispose_engine())
        monkeypatch.delenv("APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST", raising=False)
        get_settings.cache_clear()
