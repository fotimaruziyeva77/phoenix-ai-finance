"""Settings / env validation (isolated from repo .env via chdir)."""

import pytest
from app.core.config import Settings, get_settings
from cryptography.fernet import Fernet
from pydantic import ValidationError

_STRICT_OK_FERNET = Fernet.generate_key().decode()


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """No project .env file; only explicit env vars apply."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("APP_LOG_REQUEST_BODY", "false")
    monkeypatch.setenv("APP_EXPOSE_ERROR_DETAILS", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_production_without_database_url_raises(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "DATABASE_URL" in str(exc.value).upper() or "database" in str(
        exc.value
    ).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_production_with_reload_raises(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "true")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "reload" in str(exc.value).lower()


def test_invalid_log_level_raises(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_LOG_LEVEL", "not_a_level")

    with pytest.raises(ValidationError):
        Settings()


def test_empty_environment_raises(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "   ")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "environment" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_production_succeeds_with_database_url(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "x" * 32,
    )
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")

    s = Settings()
    assert s.environment == deploy_env
    assert s.database_url is not None


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_rejects_zero_ai_daily_cap(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "0")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "1000000")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "AI_DAILY" in str(exc.value).upper() or "daily" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_rejects_zero_ai_monthly_owner_cap(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "0")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "MONTHLY" in str(exc.value).upper() or "owner" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_production_without_jwt_secret_raises(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "jwt" in str(exc.value).lower() or "secret" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_production_short_jwt_secret_raises(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "short")
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "32" in str(exc.value) or "jwt" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_requires_telegram_fernet_key(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")
    monkeypatch.delenv("APP_TELEGRAM_TOKEN_FERNET_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_TOKEN_FERNET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "TELEGRAM" in str(exc.value).upper() or "fernet" in str(exc.value).lower()


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_rejects_invalid_telegram_fernet_key(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", "not-valid-fernet")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "TELEGRAM" in str(exc.value).upper() or "fernet" in str(exc.value).lower()


def test_local_short_jwt_secret_when_set_raises(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "local")
    monkeypatch.setenv("JWT_SECRET_KEY", "short")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "32" in str(exc.value) or "jwt" in str(exc.value).lower()


def test_local_invalid_telegram_fernet_when_set_raises(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "local")
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", "not-valid-fernet")

    with pytest.raises(ValidationError) as exc:
        Settings()

    assert "TELEGRAM" in str(exc.value).upper() or "fernet" in str(exc.value).lower()


def test_local_default_does_not_deny_empty_widget_allowlist(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "local")
    s = Settings()
    assert s.public_widget_deny_empty_origin_allowlist_effective is False
    assert s.public_widget_allow_allowlist_wildcard_patterns_effective is True


def test_local_force_deny_empty_matches_strict_empty_behavior(isolated_env, monkeypatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "local")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_FORCE_DENY_EMPTY_ORIGIN_ALLOWLIST", "true")
    s = Settings()
    assert s.public_widget_deny_empty_origin_allowlist_effective is True


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_denies_empty_widget_allowlist_by_default(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")

    s = Settings()
    assert s.public_widget_deny_empty_origin_allowlist_effective is True
    assert s.public_widget_allow_allowlist_wildcard_patterns_effective is False


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_allow_empty_opt_in_disables_deny_empty(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ALLOW_EMPTY_ORIGIN_ALLOWLIST", "true")

    s = Settings()
    assert s.public_widget_deny_empty_origin_allowlist_effective is False


@pytest.mark.parametrize("deploy_env", ["production", "staging"])
def test_strict_deploy_explicit_wildcard_patterns_enabled(isolated_env, monkeypatch, deploy_env):
    monkeypatch.setenv("APP_ENVIRONMENT", deploy_env)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/db")
    monkeypatch.setenv("APP_RELOAD", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("APP_TELEGRAM_TOKEN_FERNET_KEY", _STRICT_OK_FERNET)
    monkeypatch.setenv("APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT", "500000")
    monkeypatch.setenv("APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER", "5000000")
    monkeypatch.setenv("APP_PUBLIC_WIDGET_ALLOW_ALLOWLIST_WILDCARD_PATTERNS", "true")

    s = Settings()
    assert s.public_widget_allow_allowlist_wildcard_patterns_effective is True
