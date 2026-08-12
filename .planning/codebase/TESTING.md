# Testing Patterns

**Analysis Date:** 2026-05-30

## Test Framework

**Runner:**
- pytest
- Config: `pytest.ini` (project root)
- `asyncio_mode = auto` — all `async def test_` functions run automatically under the event loop
- `asyncio_default_fixture_loop_scope = function` — each test gets its own event loop

**Assertion Library:**
- Standard pytest assertions (no `unittest.TestCase`)

**Async Helper:**
- Many unit tests wrap async code in `asyncio.run()` inside a sync `def test_` (395 occurrences across 74 files); both patterns coexist:
  - `async def test_foo()` — for pytest-asyncio (integration tests, fixture-heavy)
  - `def test_foo(): asyncio.run(run())` — inline async for unit tests with httpx mocks

**Run Commands:**
```bash
pytest                        # Run all tests (unit only; integration skipped if no DB)
pytest -m integration         # Run integration tests (requires TEST_DATABASE_URL)
pytest tests/test_lead_scoring.py  # Run a single file
pytest -x                     # Stop on first failure
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (flat + one `tests/integration/` subdirectory)
- NOT co-located with source; `pythonpath = .` in `pytest.ini` allows `from app.*` imports

**Naming:**
- Unit tests: `test_<module>_<variant>.py` — e.g. `test_lead_scoring.py`, `test_gemini_provider.py`
- Integration tests suffix: `test_<area>_integration.py` — e.g. `test_leads_api_integration.py`
- Unit-only marker in name: `test_<area>_unit.py` — e.g. `test_rbac_authz_unit.py`, `test_vector_cosine_unit.py`
- Sub-folder: `tests/integration/` contains auth foundation integration tests with shared `conftest.py`

**Structure:**
```
tests/
├── conftest.py                          # Root fixtures: client, settings cache clear
├── integration_db.py                    # DB URL resolution helper
├── integration/
│   ├── conftest.py                      # Integration DB fixtures + autouse alembic upgrade
│   ├── auth_fixtures.py                 # Auth-specific fixtures
│   └── test_auth_foundation_*.py
├── fixtures/                            # Shared test data helpers
│   ├── knowledge_ingestion_harness.py
│   └── telegram_provisioning_harness.py
├── test_<unit_subject>.py               # Unit tests (no DB)
└── test_<subject>_integration.py        # Integration tests (requires TEST_DATABASE_URL)
```

## Test Structure

**Suite Organization:**
```python
"""Module docstring describing what is being tested and scope."""

from __future__ import annotations

import pytest
from app.services.lead_scoring import score_lead, LeadScoringConfig

# --- 1. Named section header for logical group ---

def test_<condition_and_expectation>() -> None:
    """One-liner docstring stating the invariant being tested."""
    r = score_lead(
        niche_id="education",
        detected_intent=None,
        collected_data_json={},
    )
    assert r.score == 0
    assert r.temperature == "cold"


# --- 2. Next section ---

@pytest.mark.parametrize("niche_id,data", [...])
def test_<variant>(niche_id: str, data: dict) -> None:
    ...
```

**Section Comments:**
- Tests grouped with `# --- N. Description ---` comment headers within a file

**Patterns:**
- No `setUp`/`tearDown` — pytest fixtures handle setup/teardown
- Fixtures declared at module level with `@pytest.fixture`; integration fixtures use `scope="module"` + `autouse=True` for Alembic upgrades
- Global `autouse=True` fixture in `tests/conftest.py` clears `get_settings` cache after every test
- `monkeypatch` used to isolate environment variables and working directory in JWT/settings tests

## Mocking

**Framework:** `unittest.mock` (`AsyncMock`, `MagicMock`, `patch`) — 668 occurrences across 53 files

**Patterns:**
```python
# Patch a class at import site (service dependency)
with patch("app.services.ai_usage_aggregation_service.AIUsageAggregateRepository") as RepoCls:
    inst = RepoCls.return_value
    inst.compute_daily_rollups_utc = AsyncMock(return_value=rollups)
    inst.replace_materialized_day = AsyncMock()
    svc = AIUsageAggregationService(maker)
    n = await svc.refresh_materialized_utc_day(d)
    inst.compute_daily_rollups_utc.assert_awaited_once_with(d)

# Patch asyncio.sleep to make retry tests fast
with patch("app.integrations.providers.gemini.asyncio.sleep", new_callable=AsyncMock):
    ...

# AsyncMock session for unit testing repositories
session = AsyncMock()
session.commit = AsyncMock()
```

**HTTP Mocking (preferred for provider tests):**
- `httpx.MockTransport` with a handler function — used in `test_gemini_provider.py`, `test_ai_providers.py`
- `httpx.ASGITransport` — used in integration tests with the FastAPI app
- FastAPI `app.dependency_overrides` — used to inject stub services (e.g. `_StubBotChatTestService`) without real dependencies

```python
# httpx.MockTransport pattern
def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={...})

async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="...") as client:
    provider = GeminiProvider(api_key="secret", http_client=client)
    out = await provider.generate_response(...)

# Dependency override pattern
app.dependency_overrides[deps.get_current_user_required] = lambda: _user
app.dependency_overrides[deps.get_bot_chat_test_service] = lambda: _StubBotChatTestService()
# ...test...
app.dependency_overrides.clear()
```

**What to Mock:**
- External HTTP calls (Stripe API, Gemini API, Telegram API) — always mock in unit tests
- Database sessions and repositories when testing service orchestration logic only
- `asyncio.sleep` in retry loop tests to avoid test latency

**What NOT to Mock:**
- Pure business logic with no I/O (e.g. `score_lead`, `plan_response_strategy`) — call directly
- Alembic schema upgrades in integration tests — run against real test DB

## Fixtures and Factories

**Root Conftest Fixtures (`tests/conftest.py`):**
```python
@pytest.fixture(autouse=True)
def _clear_settings_cache_after_test():
    yield
    from app.core.config import get_settings
    get_settings.cache_clear()

@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
```

**Integration Fixture Pattern:**
```python
# Alembic upgrade runs once per module before any tests
@pytest.fixture(scope="module", autouse=True)
def _alembic_for_module() -> None:
    url = _integration_db_url()
    assert url is not None
    _alembic_upgrade_head(url)

# Async HTTP client over ASGITransport wired to test DB
@pytest.fixture
async def leads_client(monkeypatch: pytest.MonkeyPatch, ...) -> AsyncIterator[httpx.AsyncClient]:
    # monkeypatch env, reconfigure settings, yield client
    ...
```

**Settings Fixtures:**
```python
@pytest.fixture
def jwt_settings(monkeypatch, tmp_path) -> Settings:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JWT_SECRET_KEY", "unit_test_jwt_secret_key_min_32_chars!!")
    get_settings.cache_clear()
    s = Settings()
    yield s
    get_settings.cache_clear()
```

**Test Data:**
- Inline construction with real model constructors — no factory libraries (`factory_boy`, etc.)
- Helper builder functions prefixed with `_` when reused across tests in a file (e.g. `_qp()`, `_plan()`, `_settings_full()`)
- Shared fixtures in `tests/fixtures/` for complex harnesses (knowledge ingestion, Telegram provisioning)

**Location:**
- File-local helpers: private `_` functions at module level in test file
- Cross-file helpers: `tests/fixtures/`, `tests/integration/auth_fixtures.py`
- DB URL resolution: `tests/integration_db.py`

## Coverage

**Requirements:** No numeric coverage threshold enforced in config

**View Coverage:**
```bash
pytest --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Scope: pure logic functions, single service methods, schema validation, data transformations
- No database, no HTTP (or httpx.MockTransport for provider tests)
- Synchronous `asyncio.run()` wrapper pattern common: `def test_foo(): asyncio.run(run())`
- Examples: `test_lead_scoring.py`, `test_gemini_provider.py`, `test_conversation_state_machine.py`

**Integration Tests (DB-backed):**
- Marked with `@pytest.mark.integration`
- Require `TEST_DATABASE_URL` or host-reachable `DATABASE_URL` env var
- Alembic `upgrade head` run automatically via `autouse=True` module-scoped fixture
- Use real `AsyncSession` against test PostgreSQL
- `pytest.mark.skipif(not _integration_db_url(), ...)` guards each file
- Examples: `test_leads_api_integration.py`, `test_bot_service_integration.py`

**API Integration Tests:**
- Use `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` for full ASGI stack
- Wire test DB via monkeypatched env vars and `get_settings.cache_clear()`
- Examples: `test_auth_api_integration.py`, `test_bot_chat_api_integration.py`

**HTTP Unit Tests (no DB, no real HTTP):**
- Use `fastapi.testclient.TestClient` with `dependency_overrides` to inject stubs
- Examples: `test_bot_chat_api.py`, `test_error_responses.py`, `test_hardening_security.py`

**E2E / Journey Tests:**
- `pytest.mark.mvp_journey` — single-chain MVP product verification: `test_mvp_product_journey_integration.py`
- `pytest.mark.telegram_provisioning_e2e` — full TelegramConfigService + DB path

## Common Patterns

**Async Testing (asyncio.run wrapper):**
```python
def test_mocked_success_response_normalized_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={...})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="...") as client:
            p = GeminiProvider(api_key="secret", http_client=client)
            out = await p.generate_response(...)
            assert out.success is True

    asyncio.run(run())
```

**Async Testing (pytest-asyncio native):**
```python
async def test_lead_creation_commits_session(...) -> None:
    # direct async test — asyncio_mode = auto handles event loop
    result = await service.create_lead(...)
    assert result.id is not None
```

**Error Testing:**
```python
def test_token_wrong_kind_rejected(jwt_settings: Settings):
    token = create_access_token(uid, ..., settings=jwt_settings)
    with pytest.raises(TokenTypeError):
        decode_token(token, settings=jwt_settings, expected_token_type="refresh")
```

**Boundary / Contract Guards:**
```python
# Freeze the expected public shape of a dataclass as a constant
_EXPECTED_NORMALIZED_AI_RESULT_FIELD_NAMES: frozenset[str] = frozenset({
    "success", "provider_name", "text", "model_name",
    "tokens", "raw_usage", "error_code", "error_message",
})

def test_normalized_ai_result_field_contract_is_stable() -> None:
    actual = frozenset(f.name for f in dataclasses.fields(NormalizedAIResult))
    assert actual == _EXPECTED_NORMALIZED_AI_RESULT_FIELD_NAMES
```

**Secret Hygiene Tests:**
```python
def test_error_message_redacts_google_api_key_pattern() -> None:
    # Verify that leaked keys are redacted in error output
    leaked = "AIzaSy0123456789..."
    ...
    assert leaked not in out.error_message
    assert "[REDACTED]" in out.error_message
```

**Log Inspection:**
```python
def test_gemini_provider_emits_no_logs_on_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    ...
    assert "should-not-appear-in-logs" not in caplog.text
```

**Integration Skipif Guard (every integration file):**
```python
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _integration_db_url(),
        reason="Set TEST_DATABASE_URL ...",
    ),
]
```

---

*Testing analysis: 2026-05-30*
