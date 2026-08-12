from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ALLOWED_LOG_LEVELS = frozenset(
    {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}
)

# Environments that must satisfy production-like safety checks (DB, JWT, no dev flags).
_STRICT_DEPLOY_ENVIRONMENTS = frozenset({"production", "prod", "staging"})

_LOG = logging.getLogger("app.settings")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    app_name: str = Field(default="API", min_length=1, max_length=128)
    app_version: str = Field(
        default="0.1.0",
        min_length=1,
        max_length=64,
        validation_alias=AliasChoices("APP_VERSION", "APP_APP_VERSION"),
        description="Build or release id; env APP_VERSION or APP_APP_VERSION (Dockerfile maps APP_VERSION→APP_APP_VERSION).",
    )
    service_name: str = Field(default="api", min_length=1, max_length=64)
    environment: str = Field(
        default="local",
        min_length=1,
        max_length=64,
        description=(
            "Deployment tier: e.g. local, docker (Compose), staging, production. "
            "staging and production enforce strict safety checks (see validate_production_constraints)."
        ),
    )

    host: str = Field(default="0.0.0.0", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)
    use_uvicorn_access_log: bool = Field(
        default=False,
        description="If True, uvicorn access logger stays at INFO (duplicate of structured request logs).",
    )
    log_request_body: bool = Field(
        default=False,
        description="If true, may log request details (disallowed in staging/production).",
    )

    expose_docs: bool = Field(default=True)
    expose_error_details: bool = Field(
        default=False,
        description="If true, non-validation errors may include extra fields (never stack traces); false in staging/production.",
    )

    error_tracking_enabled: bool = Field(
        default=True,
        description="When false, no events are sent to external error tracking even if a DSN is set.",
    )
    error_tracking_sentry_dsn: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SENTRY_DSN", "APP_SENTRY_DSN"),
        description="Sentry DSN; leave unset for local/dev. Optional dependency: sentry-sdk.",
    )
    error_tracking_traces_sample_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sentry performance tracing sample rate (0 = disabled).",
    )
    error_tracking_release: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SENTRY_RELEASE", "APP_SENTRY_RELEASE"),
        description="Optional release/version string (e.g. git SHA) for error grouping.",
    )

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "APP_DATABASE_URL"),
        description="Async PostgreSQL URL, e.g. postgresql+asyncpg://user:pass@host:5432/dbname",
    )
    database_echo: bool = Field(default=False)

    cors_origins: Annotated[
        list[str],
        NoDecode,
    ] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Browser origins allowed for CORS (comma-separated in APP_CORS_ORIGINS).",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        description="If true, sets Access-Control-Allow-Credentials (requires non-wildcard origins).",
    )

    trust_forwarded_for: bool = Field(
        default=False,
        description=(
            "If true, client IP for rate limits and audit uses the first X-Forwarded-For hop. "
            "Enable only behind a trusted reverse proxy."
        ),
    )

    rate_limiting_enabled: bool = Field(
        default=True,
        description="Enable rate limits for auth, OAuth, knowledge uploads, and public widget (Redis-backed when URL set).",
    )
    rate_limit_login_per_minute: int = Field(default=10, ge=0, le=10_000)
    rate_limit_register_per_minute: int = Field(default=5, ge=0, le=10_000)
    rate_limit_refresh_per_minute: int = Field(default=30, ge=0, le=10_000)
    rate_limit_oauth_start_per_minute: int = Field(default=20, ge=0, le=10_000)
    rate_limit_oauth_callback_per_minute: int = Field(default=40, ge=0, le=10_000)
    rate_limit_oauth_exchange_per_minute: int = Field(default=30, ge=0, le=10_000)
    rate_limit_logout_per_minute: int = Field(default=60, ge=0, le=10_000)
    rate_limit_forgot_password_per_minute: int = Field(
        default=3,
        ge=0,
        le=10_000,
        description="Max forgot-password requests per IP per minute (prevents email enumeration).",
    )
    rate_limit_reset_password_per_minute: int = Field(
        default=5,
        ge=0,
        le=10_000,
        description="Max reset-password attempts per IP per minute.",
    )
    rate_limit_public_widget_chat_per_minute: int = Field(
        default=30,
        ge=0,
        le=10_000,
        description="Max public widget chat POSTs per client IP per widget key per minute (0 = off).",
    )
    rate_limit_public_widget_bootstrap_per_minute: int = Field(
        default=120,
        ge=0,
        le=10_000,
        description="Max public widget bootstrap GETs per IP per widget key per minute (0 = off).",
    )
    rate_limit_telegram_webhook_per_minute: int = Field(
        default=60,
        ge=0,
        le=10_000,
        description="Max Telegram webhook POSTs per bot_id per minute (0 = off).",
    )

    rate_limit_redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "REDIS_URL",
            "RATE_LIMIT_REDIS_URL",
            "APP_REDIS_URL",
            "APP_RATE_LIMIT_REDIS_URL",
        ),
        description=(
            "Redis URL for distributed rate limits and widget abuse (e.g. redis://localhost:6379/1). "
            "Unset = in-process limiters (not safe across multiple workers)."
        ),
    )
    rate_limit_redis_key_prefix: str = Field(
        default="bf:rl",
        min_length=1,
        max_length=128,
        description="Prefix for Redis keys used by sliding-window limiter and widget streak tracker.",
    )
    rate_limit_redis_connect_timeout_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    rate_limit_redis_socket_timeout_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    rate_limit_auth_fail_closed_on_redis_error: bool = Field(
        default=True,
        description="On Redis errors during auth/OAuth/knowledge rate checks, deny with 503.",
    )
    rate_limit_public_fail_open_on_redis_error: bool = Field(
        default=True,
        description="On Redis errors during public widget rate/abuse checks, allow the request (availability).",
    )

    public_widget_abuse_enabled: bool = Field(
        default=True,
        description="Session/content heuristics for public widget chat (see app.core.public_widget_abuse).",
    )
    public_widget_abuse_session_burst_per_minute: int = Field(
        default=15,
        ge=0,
        le=500,
        description="Max chat messages per visitor session (or IP before session) per widget per rolling minute (0 = off).",
    )
    public_widget_abuse_identical_total_per_window: int = Field(
        default=6,
        ge=0,
        le=100,
        description="Max identical normalized messages per session per window (0 = off).",
    )
    public_widget_abuse_identical_window_seconds: float = Field(
        default=300.0,
        ge=30.0,
        le=3600.0,
        description="Window for identical-message counting.",
    )
    public_widget_abuse_max_consecutive_identical: int = Field(
        default=6,
        ge=0,
        le=50,
        description="Block when the same normalized message is sent this many times in a row (0 = off).",
    )
    public_widget_abuse_max_message_chars: int = Field(
        default=12_000,
        ge=0,
        le=32_000,
        description="Reject chat bodies longer than this (0 = only schema max applies).",
    )
    public_widget_origin_loopback_equivalent: bool = Field(
        default=True,
        description=(
            "Treat localhost, 127.0.0.1, ::1, and [::1] as interchangeable when matching the "
            "widget allowlist, if any loopback host is listed. Does not relax non-loopback rules."
        ),
    )
    public_widget_allow_empty_origin_allowlist: bool = Field(
        default=False,
        description=(
            "Strict deploys only (staging/production/prod): when true, an empty allowed_domains list "
            "allows embedding from any origin (unsafe). Default false = deny until domains are configured."
        ),
    )
    public_widget_force_deny_empty_origin_allowlist: bool = Field(
        default=False,
        description=(
            "Non-strict environments only: when true, treat an empty allowlist like production (deny). "
            "Use for local E2E/tests of strict behavior without changing APP_ENVIRONMENT."
        ),
    )
    public_widget_allow_allowlist_wildcard_patterns: bool | None = Field(
        default=None,
        description=(
            "When null (default): allow *. and leading-dot patterns in local/docker; disallow in "
            "staging/production/prod unless set to true. When false, PATCH allowlist rejects wildcards."
        ),
    )

    jwt_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "APP_JWT_SECRET_KEY"),
        description="Symmetric key for signing JWTs (required in production; use a long random value).",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm (HS256, HS384, or HS512).",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=24 * 60,
        description="Access token lifetime in minutes.",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        le=366,
        description="Refresh token lifetime in days.",
    )

    # -------------------------------------------------------------------------
    # Email delivery (Resend)
    # -------------------------------------------------------------------------
    resend_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RESEND_API_KEY", "APP_RESEND_API_KEY"),
        description="Resend.com API key for transactional emails (verification, password reset).",
    )
    email_from_address: str = Field(
        default="noreply@botforge.ai",
        validation_alias=AliasChoices("EMAIL_FROM_ADDRESS", "APP_EMAIL_FROM_ADDRESS"),
        description="Sender address shown on outgoing emails.",
    )
    email_from_name: str = Field(
        default="BotForge AI",
        validation_alias=AliasChoices("EMAIL_FROM_NAME", "APP_EMAIL_FROM_NAME"),
        description="Sender display name for outgoing emails.",
    )
    email_verification_token_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        ge=300,
        description="How long email verification tokens stay valid (seconds).",
    )
    email_password_reset_token_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        ge=300,
        description="How long password-reset tokens stay valid (seconds).",
    )
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("FRONTEND_BASE_URL", "APP_FRONTEND_BASE_URL"),
        description="Public frontend base URL for building email action links.",
    )

    # -------------------------------------------------------------------------
    # Stripe (payments)
    # -------------------------------------------------------------------------
    stripe_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_SECRET_KEY", "APP_STRIPE_SECRET_KEY"),
        description="Stripe secret key (sk_live_… or sk_test_…).",
    )
    stripe_publishable_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_PUBLISHABLE_KEY", "APP_STRIPE_PUBLISHABLE_KEY"),
        description="Stripe publishable key exposed to the frontend.",
    )
    stripe_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_WEBHOOK_SECRET", "APP_STRIPE_WEBHOOK_SECRET"),
        description="Stripe webhook endpoint signing secret (whsec_…).",
    )
    # Per-plan Stripe Price IDs (monthly recurring)
    stripe_price_id_pro: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_PRICE_ID_PRO", "APP_STRIPE_PRICE_ID_PRO"),
    )
    stripe_price_id_business: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_PRICE_ID_BUSINESS", "APP_STRIPE_PRICE_ID_BUSINESS"),
    )
    stripe_price_id_enterprise: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STRIPE_PRICE_ID_ENTERPRISE", "APP_STRIPE_PRICE_ID_ENTERPRISE"),
    )

    def stripe_price_id_for(self, plan_slug: str) -> str | None:
        """Look up the Stripe Price ID for a plan slug."""
        mapping = {
            "pro": self.stripe_price_id_pro,
            "business": self.stripe_price_id_business,
            "enterprise": self.stripe_price_id_enterprise,
        }
        return mapping.get(plan_slug)

    telegram_token_fernet_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_TOKEN_FERNET_KEY",
            "APP_TELEGRAM_TOKEN_FERNET_KEY",
        ),
        description=(
            "Fernet key (from cryptography.fernet.Fernet.generate_key()) for Telegram "
            "bot tokens and webhook secret_token at rest. Required in staging/production. "
            "Independent of JWT_SECRET_KEY — rotating JWT must not affect Telegram ciphertexts."
        ),
    )

    public_api_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PUBLIC_API_BASE_URL", "APP_PUBLIC_API_BASE_URL"),
        description=(
            "Public HTTPS origin of this API as seen by Telegram (e.g. https://api.example.com). "
            "Used to build webhook URLs for bot connect. No trailing path; must match TLS cert."
        ),
    )

    google_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "APP_GOOGLE_OAUTH_CLIENT_ID"),
        description="Google OAuth 2.0 Web client ID (Google Cloud Console).",
    )
    google_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET", "APP_GOOGLE_OAUTH_CLIENT_SECRET"),
        description="Google OAuth client secret (server-side only; never expose to browsers).",
    )
    google_oauth_redirect_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_OAUTH_REDIRECT_URI", "APP_GOOGLE_OAUTH_REDIRECT_URI"),
        description="Registered redirect URI for the authorization code callback (backend URL).",
    )
    frontend_oauth_redirect_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FRONTEND_OAUTH_REDIRECT_URL",
            "APP_FRONTEND_OAUTH_REDIRECT_URL",
        ),
        description=(
            "SPA URL after OAuth provider callback (query: oauth_exchange_code or oauth_error)."
        ),
    )

    github_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_ID", "APP_GITHUB_OAUTH_CLIENT_ID"),
        description="GitHub OAuth App client ID.",
    )
    github_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_CLIENT_SECRET", "APP_GITHUB_OAUTH_CLIENT_SECRET"),
        description="GitHub OAuth client secret (server-only).",
    )
    github_oauth_redirect_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_OAUTH_REDIRECT_URI", "APP_GITHUB_OAUTH_REDIRECT_URI"),
        description="Registered GitHub OAuth callback URL (backend).",
    )

    auth_cookie_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTH_COOKIE_ENABLED", "APP_AUTH_COOKIE_ENABLED"),
        description=(
            "If true, issue HttpOnly access/refresh cookies and a CSRF cookie on login/register/refresh/OAuth; "
            "SPA should use credentials: 'include' and send X-CSRF-Token on mutating requests."
        ),
    )
    auth_cookie_omit_body_tokens: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTH_COOKIE_OMIT_BODY_TOKENS", "APP_AUTH_COOKIE_OMIT_BODY_TOKENS"),
        description=(
            "When auth_cookie_enabled, omit access_token/refresh_token from JSON bodies (tokens only in cookies). "
            "Requires a cookie-aware frontend."
        ),
    )
    auth_cookie_secure: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTH_COOKIE_SECURE", "APP_AUTH_COOKIE_SECURE"),
        description="Set Secure flag on auth cookies; if unset, defaults to true in staging/production.",
    )
    auth_cookie_same_site: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias=AliasChoices("AUTH_COOKIE_SAMESITE", "APP_AUTH_COOKIE_SAMESITE"),
        description="SameSite for auth cookies (use 'none' only with HTTPS and Secure).",
    )
    auth_cookie_domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AUTH_COOKIE_DOMAIN", "APP_AUTH_COOKIE_DOMAIN"),
        description="Optional cookie Domain attribute (e.g. .example.com for subdomains).",
    )
    auth_cookie_path: str = Field(
        default="/",
        min_length=1,
        max_length=256,
        validation_alias=AliasChoices("AUTH_COOKIE_PATH", "APP_AUTH_COOKIE_PATH"),
    )
    auth_access_cookie_name: str = Field(
        default="bf_access",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("AUTH_ACCESS_COOKIE_NAME", "APP_AUTH_ACCESS_COOKIE_NAME"),
    )
    auth_refresh_cookie_name: str = Field(
        default="bf_refresh",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("AUTH_REFRESH_COOKIE_NAME", "APP_AUTH_REFRESH_COOKIE_NAME"),
    )
    auth_csrf_cookie_name: str = Field(
        default="bf_csrf",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("AUTH_CSRF_COOKIE_NAME", "APP_AUTH_CSRF_COOKIE_NAME"),
    )
    auth_csrf_header_name: str = Field(
        default="X-CSRF-Token",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("AUTH_CSRF_HEADER_NAME", "APP_AUTH_CSRF_HEADER_NAME"),
    )

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "APP_GEMINI_API_KEY"),
        description="Google AI Studio / Gemini API key for generative calls.",
    )
    gemini_default_model: str = Field(
        default="gemini-2.5-flash",
        min_length=1,
        max_length=160,
        validation_alias=AliasChoices("GEMINI_DEFAULT_MODEL", "APP_GEMINI_DEFAULT_MODEL"),
        description="Model id when GenerateParams.model is empty (e.g. gemini-2.5-flash).",
    )
    gemini_api_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        min_length=8,
        max_length=256,
        validation_alias=AliasChoices("GEMINI_API_BASE_URL", "APP_GEMINI_API_BASE_URL"),
        description="Gemini Generative Language API base URL (no trailing path after v1beta).",
    )
    gemini_request_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        validation_alias=AliasChoices(
            "GEMINI_REQUEST_TIMEOUT_SECONDS",
            "APP_GEMINI_REQUEST_TIMEOUT_SECONDS",
        ),
        description="HTTP read/write timeout for Gemini generateContent calls.",
    )
    gemini_connect_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        validation_alias=AliasChoices(
            "GEMINI_CONNECT_TIMEOUT_SECONDS",
            "APP_GEMINI_CONNECT_TIMEOUT_SECONDS",
        ),
        description="HTTP connect timeout for Gemini API.",
    )
    gemini_send_thinking_config: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "GEMINI_SEND_THINKING_CONFIG",
            "APP_GEMINI_SEND_THINKING_CONFIG",
        ),
        description=(
            "When True, send generationConfig.thinkingConfig for Gemini 2.5+ models that support it. "
            "Disable if your API version rejects the field."
        ),
    )
    gemini_thinking_budget: int = Field(
        default=0,
        ge=-1,
        le=24576,
        validation_alias=AliasChoices(
            "GEMINI_THINKING_BUDGET",
            "APP_GEMINI_THINKING_BUDGET",
        ),
        description=(
            "thinkingBudget passed to Gemini 2.5+ (see Google thinking docs). "
            "0 disables internal reasoning tokens (much lower billed output on simple chats). "
            "-1 leaves dynamic thinking to the model."
        ),
    )

    # --- Ollama (local LLM, cost-free alternative to Gemini) ---
    ollama_base_url: str = Field(
        default="http://ollama:11434",
        min_length=8,
        max_length=256,
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "APP_OLLAMA_BASE_URL"),
        description="Ollama API base URL (Docker service or localhost).",
    )
    ollama_default_model: str = Field(
        default="qwen2.5:7b",
        min_length=1,
        max_length=160,
        validation_alias=AliasChoices("OLLAMA_DEFAULT_MODEL", "APP_OLLAMA_DEFAULT_MODEL"),
        description="Default Ollama model for bot responses (e.g. qwen2.5:7b, llama3.1:8b).",
    )
    ollama_request_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        validation_alias=AliasChoices(
            "OLLAMA_REQUEST_TIMEOUT_SECONDS",
            "APP_OLLAMA_REQUEST_TIMEOUT_SECONDS",
        ),
        description="HTTP read/write timeout for Ollama /api/chat calls.",
    )
    ollama_connect_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=120.0,
        validation_alias=AliasChoices(
            "OLLAMA_CONNECT_TIMEOUT_SECONDS",
            "APP_OLLAMA_CONNECT_TIMEOUT_SECONDS",
        ),
        description="HTTP connect timeout for Ollama API.",
    )

    ai_semantic_cache_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_ENABLED",
            "APP_AI_SEMANTIC_CACHE_ENABLED",
        ),
        description=(
            "When True and Redis + GEMINI_API_KEY are configured, short user messages may reuse "
            "prior assistant replies via embedding similarity (skips chat completion tokens on hit)."
        ),
    )
    ai_semantic_cache_redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_REDIS_URL",
            "APP_AI_SEMANTIC_CACHE_REDIS_URL",
        ),
        description="Optional dedicated Redis URL for semantic cache; defaults to rate-limit Redis URL.",
    )
    ai_semantic_cache_key_prefix: str = Field(
        default="bf:ai:sc",
        min_length=2,
        max_length=64,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_KEY_PREFIX",
            "APP_AI_SEMANTIC_CACHE_KEY_PREFIX",
        ),
        description="Prefix for per-bot semantic cache Redis keys.",
    )
    ai_semantic_cache_similarity_threshold: float = Field(
        default=0.95,
        ge=0.75,
        le=1.0,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_SIMILARITY_THRESHOLD",
            "APP_AI_SEMANTIC_CACHE_SIMILARITY_THRESHOLD",
        ),
        description="Cosine similarity floor for cache hits (1.0 = identical direction in embedding space).",
    )
    ai_semantic_cache_max_entries_per_bot: int = Field(
        default=200,
        ge=8,
        le=2000,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_MAX_ENTRIES_PER_BOT",
            "APP_AI_SEMANTIC_CACHE_MAX_ENTRIES_PER_BOT",
        ),
        description="Max cached query/response pairs stored per bot_id (Redis list, newest first).",
    )
    ai_semantic_cache_max_message_chars: int = Field(
        default=256,
        ge=32,
        le=4096,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_MAX_MESSAGE_CHARS",
            "APP_AI_SEMANTIC_CACHE_MAX_MESSAGE_CHARS",
        ),
        description="Do not attempt semantic cache for user text longer than this many characters.",
    )
    ai_semantic_cache_max_words: int = Field(
        default=8,
        ge=1,
        le=64,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_MAX_WORDS",
            "APP_AI_SEMANTIC_CACHE_MAX_WORDS",
        ),
        description="Do not attempt semantic cache when the user message has more than this many whitespace tokens.",
    )
    ai_semantic_cache_embedding_model: str = Field(
        default="models/text-embedding-004",
        min_length=4,
        max_length=120,
        validation_alias=AliasChoices(
            "EMBEDDING_MODEL",
            "APP_EMBEDDING_MODEL",
            "AI_SEMANTIC_CACHE_EMBEDDING_MODEL",
            "APP_AI_SEMANTIC_CACHE_EMBEDDING_MODEL",
        ),
        description=(
            "Gemini ``embedContent`` model resource id (e.g. ``models/text-embedding-004``). "
            "Prefer env ``EMBEDDING_MODEL`` (or ``APP_EMBEDDING_MODEL``). "
            "Embedding HTTP calls use API **v1** (see ``app.integrations.gemini_text_embedding``)."
        ),
    )
    ai_semantic_cache_entry_ttl_seconds: int = Field(
        default=86_400,
        ge=60,
        le=864_000,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_ENTRY_TTL_SECONDS",
            "APP_AI_SEMANTIC_CACHE_ENTRY_TTL_SECONDS",
        ),
        description="TTL (seconds) stored on each cache entry; expired entries are ignored on read.",
    )
    ai_semantic_cache_strict_embedding: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AI_SEMANTIC_CACHE_STRICT_EMBEDDING",
            "APP_AI_SEMANTIC_CACHE_STRICT_EMBEDDING",
        ),
        description=(
            "When False (default, production-safe): embedding failures during semantic cache lookup "
            "are logged and the cache step is skipped — the main LLM response always proceeds. "
            "When True (strict / legacy mode): embedding failures block the chat response and return "
            "an error to the client. Enable strict mode only to explicitly test the embedding-error path."
        ),
    )
    ai_exact_cache_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_EXACT_CACHE_ENABLED",
            "APP_AI_EXACT_CACHE_ENABLED",
        ),
        description=(
            "When True and Redis is configured, normalized user text may hit an exact-match reply cache "
            "before any embedding API call (cheaper than semantic similarity)."
        ),
    )
    ai_exact_cache_key_prefix: str = Field(
        default="bf:ai:ec",
        min_length=2,
        max_length=64,
        validation_alias=AliasChoices(
            "AI_EXACT_CACHE_KEY_PREFIX",
            "APP_AI_EXACT_CACHE_KEY_PREFIX",
        ),
        description="Redis key prefix for per-bot exact completion cache entries.",
    )
    ai_exact_cache_ttl_seconds: int = Field(
        default=172_800,
        ge=60,
        le=864_000,
        validation_alias=AliasChoices(
            "AI_EXACT_CACHE_TTL_SECONDS",
            "APP_AI_EXACT_CACHE_TTL_SECONDS",
        ),
        description="TTL for exact-match cache keys (GET/SETEX).",
    )
    ai_exact_cache_max_message_chars: int = Field(
        default=2048,
        ge=32,
        le=8192,
        validation_alias=AliasChoices(
            "AI_EXACT_CACHE_MAX_MESSAGE_CHARS",
            "APP_AI_EXACT_CACHE_MAX_MESSAGE_CHARS",
        ),
        description="Skip exact cache for user messages longer than this (chars).",
    )
    ai_trivial_greeting_fast_path_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_TRIVIAL_GREETING_FAST_PATH_ENABLED",
            "APP_AI_TRIVIAL_GREETING_FAST_PATH_ENABLED",
        ),
        description=(
            "When True, ultra-short greetings / emoji-only pings return a canned reply without "
            "embedding or LLM (Layer 1). Disable in tests that must exercise the provider stack."
        ),
    )
    ai_pipeline_debug_trace_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AI_PIPELINE_DEBUG_TRACE_ENABLED",
            "APP_AI_PIPELINE_DEBUG_TRACE_ENABLED",
        ),
        description=(
            "When True, emit structured ``ai_pipeline_debug`` logs around trivial detection, "
            "completion cache, and LLM entry (temporary diagnostics)."
        ),
    )
    ai_pipeline_saved_tokens_system_chars: int = Field(
        default=3600,
        ge=0,
        le=50_000,
        validation_alias=AliasChoices(
            "AI_PIPELINE_SAVED_TOKENS_SYSTEM_CHARS",
            "APP_AI_PIPELINE_SAVED_TOKENS_SYSTEM_CHARS",
        ),
        description=(
            "Character budget added when estimating ``tokens_saved_est`` for cache/trivial paths "
            "(approximate system prompt size; not sent to the model on those paths)."
        ),
    )
    ai_prompt_slim_for_short_messages: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_PROMPT_SLIM_FOR_SHORT_MESSAGES",
            "APP_AI_PROMPT_SLIM_FOR_SHORT_MESSAGES",
        ),
        description="Use a compact system prompt + tighter history when the user message is very short.",
    )
    ai_prompt_slim_word_threshold: int = Field(
        default=3,
        ge=1,
        le=12,
        validation_alias=AliasChoices(
            "AI_PROMPT_SLIM_WORD_THRESHOLD",
            "APP_AI_PROMPT_SLIM_WORD_THRESHOLD",
        ),
        description="Apply slim prompt when trimmed user text has fewer than this many words.",
    )
    ai_prompt_slim_history_cap: int = Field(
        default=4,
        ge=1,
        le=32,
        validation_alias=AliasChoices(
            "AI_PROMPT_SLIM_HISTORY_CAP",
            "APP_AI_PROMPT_SLIM_HISTORY_CAP",
        ),
        description="When slim prompt applies, cap recent history turns to at most this many messages.",
    )

    telegram_lead_alert_bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_LEAD_ALERT_BOT_TOKEN",
            "APP_TELEGRAM_LEAD_ALERT_BOT_TOKEN",
        ),
        description="Bot token for optional new-lead Telegram alerts (server-only; never expose).",
    )
    telegram_lead_alert_chat_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_LEAD_ALERT_CHAT_ID",
            "APP_TELEGRAM_LEAD_ALERT_CHAT_ID",
        ),
        description="Telegram chat_id (user, group, or channel) for new-lead alerts.",
    )
    telegram_lead_alert_bot_username: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_LEAD_ALERT_BOT_USERNAME",
            "APP_TELEGRAM_LEAD_ALERT_BOT_USERNAME",
        ),
        description="Telegram bot @username (without @) for deep-link pairing UI.",
    )

    ai_pricing_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AI_PRICING_JSON", "APP_AI_PRICING_JSON"),
        description=(
            'Optional JSON overlay merging on built-in rates, e.g. '
            '{"providers":{"gemini":{"gemini-2.5-flash":{"input_usd_per_million":"0.30","output_usd_per_million":"2.50"}}}}'
        ),
    )
    ai_token_chars_per_token_estimate: float = Field(
        default=4.0,
        ge=1.0,
        le=64.0,
        validation_alias=AliasChoices(
            "AI_TOKEN_CHARS_PER_TOKEN_ESTIMATE",
            "APP_AI_TOKEN_CHARS_PER_TOKEN_ESTIMATE",
        ),
        description="Fallback: estimated_tokens ≈ ceil(chars / this divisor) when the provider omits usage.",
    )
    ai_max_output_tokens_ceiling: int = Field(
        default=8192,
        ge=256,
        le=128_000,
        validation_alias=AliasChoices(
            "AI_MAX_OUTPUT_TOKENS_CEILING",
            "APP_AI_MAX_OUTPUT_TOKENS_CEILING",
        ),
        description="Hard cap on max_output_tokens for every provider call (per-bot values cannot exceed this).",
    )
    ai_max_output_tokens_default: int = Field(
        default=2048,
        ge=256,
        le=128_000,
        validation_alias=AliasChoices(
            "AI_MAX_OUTPUT_TOKENS_DEFAULT",
            "APP_AI_MAX_OUTPUT_TOKENS_DEFAULT",
        ),
        description="When a bot has no per-bot max_output_tokens, use this default (still clamped to the ceiling).",
    )
    ai_daily_total_tokens_soft_cap_per_bot: int = Field(
        default=0,
        ge=0,
        le=2_147_483_647,
        validation_alias=AliasChoices(
            "AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT",
            "APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT",
        ),
        description=(
            "Hard cap: block new AI turns when sum(tokens_total) for the bot today (UTC) reaches this "
            "(0 = disabled for local/dev only). Staging/production require a positive value. "
            "Enforcement uses persisted ai_usage_logs.tokens_total per turn."
        ),
    )
    ai_monthly_total_tokens_cap_per_owner: int = Field(
        default=0,
        ge=0,
        le=2_147_483_647,
        validation_alias=AliasChoices(
            "AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER",
            "APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER",
        ),
        description=(
            "Hard cap: block AI for any bot owned by this user when sum(tokens_total) in the UTC calendar month "
            "across all their bots reaches this (0 = disabled for local/dev). Staging/production require > 0."
        ),
    )
    ai_usage_quota_warn_fraction: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        validation_alias=AliasChoices(
            "AI_USAGE_QUOTA_WARN_FRACTION",
            "APP_AI_USAGE_QUOTA_WARN_FRACTION",
        ),
        description="Emit ai_usage_near_cap logs when used_tokens >= this fraction of cap (per scope).",
    )
    ai_sales_use_model_for_intent_when_rules_miss: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "AI_SALES_USE_MODEL_FOR_INTENT_WHEN_RULES_MISS",
            "APP_AI_SALES_USE_MODEL_FOR_INTENT_WHEN_RULES_MISS",
        ),
        description=(
            "Sales funnel: when False (default), skip the extra Gemini intent call if rules miss — "
            "use deterministic sales_default (sales_interest) so the state machine stays in known-intent mode. "
            "Set True to restore legacy behavior (Gemini JSON classifier on ambiguous text)."
        ),
    )
    ai_sales_intent_gemini_ambiguity_only: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_SALES_INTENT_GEMINI_AMBIGUITY_ONLY",
            "APP_AI_SALES_INTENT_GEMINI_AMBIGUITY_ONLY",
        ),
        description=(
            "When True with ``ai_sales_use_model_for_intent_when_rules_miss`` enabled, call Gemini intent "
            "only for long / hedge-heavy / question-heavy utterances; otherwise use ``sales_default``."
        ),
    )
    ai_sales_llm_burst_protection_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AI_SALES_LLM_BURST_PROTECTION_ENABLED",
            "APP_AI_SALES_LLM_BURST_PROTECTION_ENABLED",
        ),
        description="When True and Redis is configured, cap per-bot LLM invocations in a short window for opening-style messages.",
    )
    ai_sales_llm_burst_window_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        validation_alias=AliasChoices(
            "AI_SALES_LLM_BURST_WINDOW_SECONDS",
            "APP_AI_SALES_LLM_BURST_WINDOW_SECONDS",
        ),
        description="Sliding bucket width (seconds) for counting sales intent+chat Gemini calls per bot.",
    )
    ai_sales_llm_burst_max_calls_per_window: int = Field(
        default=8,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "AI_SALES_LLM_BURST_MAX_CALLS_PER_WINDOW",
            "APP_AI_SALES_LLM_BURST_MAX_CALLS_PER_WINDOW",
        ),
        description="When in-window count reaches this, opening-style chat turns skip Gemini chat with a canned line.",
    )
    ai_sales_llm_burst_redis_key_prefix: str = Field(
        default="bf:ai:llmburst",
        min_length=4,
        max_length=64,
        validation_alias=AliasChoices(
            "AI_SALES_LLM_BURST_REDIS_KEY_PREFIX",
            "APP_AI_SALES_LLM_BURST_REDIS_KEY_PREFIX",
        ),
        description="Redis key prefix for per-bot LLM burst counters.",
    )
    ai_telegram_gemini_rate_limit_user_message_uz: str = Field(
        default=(
            "Hozir yuklama biroz yuqori. Iltimos, savolingizni 1 daqiqadan keyin qayta yuboring."
        ),
        min_length=8,
        max_length=500,
        validation_alias=AliasChoices(
            "AI_TELEGRAM_GEMINI_RATE_LIMIT_USER_MESSAGE_UZ",
            "APP_AI_TELEGRAM_GEMINI_RATE_LIMIT_USER_MESSAGE_UZ",
        ),
        description="User-facing Uzbek line when Gemini chat returns 429 after retries (sales + Telegram).",
    )
    ai_intent_classifier_cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86_400,
        validation_alias=AliasChoices(
            "AI_INTENT_CLASSIFIER_CACHE_TTL_SECONDS",
            "APP_AI_INTENT_CLASSIFIER_CACHE_TTL_SECONDS",
        ),
        description="In-process TTL for identical intent classification keys (0 = disable cache).",
    )
    ai_intent_classifier_cache_max_entries: int = Field(
        default=256,
        ge=16,
        le=10_000,
        validation_alias=AliasChoices(
            "AI_INTENT_CLASSIFIER_CACHE_MAX_ENTRIES",
            "APP_AI_INTENT_CLASSIFIER_CACHE_MAX_ENTRIES",
        ),
        description="Max cached intent outcomes per process before FIFO eviction.",
    )
    ai_knowledge_chat_context_token_budget_fraction: float = Field(
        default=0.85,
        ge=0.35,
        le=1.0,
        validation_alias=AliasChoices(
            "AI_KNOWLEDGE_CHAT_CONTEXT_TOKEN_BUDGET_FRACTION",
            "APP_AI_KNOWLEDGE_CHAT_CONTEXT_TOKEN_BUDGET_FRACTION",
        ),
        description=(
            "Non-sales dashboard chat: multiply knowledge_context_default_max_estimated_tokens by this "
            "fraction when assembling RAG context (reduces prompt tokens; full cap still applies to API overrides)."
        ),
    )
    security_enable_hsts: bool = Field(
        default=False,
        validation_alias=AliasChoices("SECURITY_ENABLE_HSTS", "APP_SECURITY_ENABLE_HSTS"),
        description="If true, send Strict-Transport-Security on responses (enable only behind HTTPS everywhere).",
    )
    security_hsts_max_age: int = Field(
        default=31_536_000,
        ge=0,
        le=63_072_000,
        validation_alias=AliasChoices("SECURITY_HSTS_MAX_AGE", "APP_SECURITY_HSTS_MAX_AGE"),
        description="HSTS max-age in seconds (default: 1 year). Only used when security_enable_hsts is true.",
    )
    security_hsts_include_subdomains: bool = Field(
        default=False,
        validation_alias=AliasChoices("SECURITY_HSTS_INCLUDE_SUBDOMAINS", "APP_SECURITY_HSTS_INCLUDE_SUBDOMAINS"),
        description="Add includeSubDomains to HSTS header.",
    )
    security_hsts_preload: bool = Field(
        default=False,
        validation_alias=AliasChoices("SECURITY_HSTS_PRELOAD", "APP_SECURITY_HSTS_PRELOAD"),
        description="Add preload to HSTS header (only enable after full HTTPS audit).",
    )
    security_csp_extra_connect_src: str = Field(
        default="",
        validation_alias=AliasChoices("SECURITY_CSP_EXTRA_CONNECT_SRC", "APP_SECURITY_CSP_EXTRA_CONNECT_SRC"),
        description="Space-separated extra origins appended to CSP connect-src (e.g. Sentry, analytics).",
    )
    security_csp_extra_script_src: str = Field(
        default="",
        validation_alias=AliasChoices("SECURITY_CSP_EXTRA_SCRIPT_SRC", "APP_SECURITY_CSP_EXTRA_SCRIPT_SRC"),
        description="Space-separated extra origins appended to CSP script-src.",
    )
    security_request_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=600.0,
        validation_alias=AliasChoices("SECURITY_REQUEST_TIMEOUT", "APP_SECURITY_REQUEST_TIMEOUT_SECONDS"),
        description="Max seconds any incoming request may run before the server returns 504.",
    )
    security_upload_timeout_seconds: float = Field(
        default=300.0,
        ge=30.0,
        le=900.0,
        validation_alias=AliasChoices("SECURITY_UPLOAD_TIMEOUT", "APP_SECURITY_UPLOAD_TIMEOUT_SECONDS"),
        description="Extended timeout for file upload endpoints (e.g. knowledge PDF).",
    )

    knowledge_pdf_max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
        validation_alias=AliasChoices(
            "KNOWLEDGE_PDF_MAX_BYTES",
            "APP_KNOWLEDGE_PDF_MAX_UPLOAD_BYTES",
        ),
    )
    knowledge_max_files_per_bot: int = Field(
        default=100,
        ge=1,
        le=10_000,
        validation_alias=AliasChoices(
            "KNOWLEDGE_MAX_FILES_PER_BOT",
            "APP_KNOWLEDGE_MAX_FILES_PER_BOT",
        ),
        description="Hard cap on knowledge files per bot (storage / abuse guardrail).",
    )
    knowledge_upload_rate_limit_per_minute: int = Field(
        default=20,
        ge=0,
        le=500,
        validation_alias=AliasChoices(
            "KNOWLEDGE_UPLOAD_RATE_LIMIT_PER_MINUTE",
            "APP_KNOWLEDGE_UPLOAD_RATE_LIMIT_PER_MINUTE",
        ),
        description="Max PDF uploads per owner+bot per minute (0 = no per-bot upload limit).",
    )
    knowledge_upload_reject_burst_limit: int = Field(
        default=25,
        ge=0,
        le=500,
        validation_alias=AliasChoices(
            "KNOWLEDGE_UPLOAD_REJECT_BURST_LIMIT",
            "APP_KNOWLEDGE_UPLOAD_REJECT_BURST_LIMIT",
        ),
        description="Log a warning after this many validation rejections per owner+bot in the burst window.",
    )
    knowledge_upload_reject_burst_window_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        validation_alias=AliasChoices(
            "KNOWLEDGE_UPLOAD_REJECT_BURST_WINDOW_SECONDS",
            "APP_KNOWLEDGE_UPLOAD_REJECT_BURST_WINDOW_SECONDS",
        ),
    )
    knowledge_pdf_magic_scan_bytes: int = Field(
        default=2048,
        ge=16,
        le=65_536,
        validation_alias=AliasChoices(
            "KNOWLEDGE_PDF_MAGIC_SCAN_BYTES",
            "APP_KNOWLEDGE_PDF_MAGIC_SCAN_BYTES",
        ),
        description="How many leading bytes to scan for a PDF signature after upload.",
    )
    knowledge_chunk_max_chars: int = Field(
        default=4000,
        ge=256,
        le=100_000,
        validation_alias=AliasChoices(
            "KNOWLEDGE_CHUNK_MAX_CHARS",
            "APP_KNOWLEDGE_CHUNK_MAX_CHARS",
        ),
        description="Maximum UTF-8 characters per stored text chunk after PDF extraction.",
    )
    knowledge_processing_error_max_chars: int = Field(
        default=8000,
        ge=256,
        le=50_000,
        validation_alias=AliasChoices(
            "KNOWLEDGE_PROCESSING_ERROR_MAX_CHARS",
            "APP_KNOWLEDGE_PROCESSING_ERROR_MAX_CHARS",
        ),
        description="Truncate processing_error messages to this length for storage stability.",
    )
    knowledge_ingestion_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "KNOWLEDGE_INGESTION_ENABLED",
            "APP_KNOWLEDGE_INGESTION_ENABLED",
        ),
        description="When true, enqueue PDF knowledge files for async extraction after upload (requires Redis URL).",
    )
    knowledge_ingestion_redis_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "KNOWLEDGE_INGESTION_REDIS_URL",
            "APP_KNOWLEDGE_INGESTION_REDIS_URL",
        ),
        description="Redis for knowledge ingestion queue; defaults to rate-limit Redis URL when unset.",
    )
    knowledge_ingestion_queue_key: str = Field(
        default="bf:knowledge:ingestion",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices(
            "KNOWLEDGE_INGESTION_QUEUE_KEY",
            "APP_KNOWLEDGE_INGESTION_QUEUE_KEY",
        ),
    )
    knowledge_ingestion_max_attempts: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "KNOWLEDGE_INGESTION_MAX_ATTEMPTS",
            "APP_KNOWLEDGE_INGESTION_MAX_ATTEMPTS",
        ),
        description="After this many failed processing runs, the file moves to dead_letter (no further auto-retries).",
    )
    knowledge_ingestion_worker_brpop_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=300,
        validation_alias=AliasChoices(
            "KNOWLEDGE_INGESTION_WORKER_BRPOP_TIMEOUT_SECONDS",
            "APP_KNOWLEDGE_INGESTION_WORKER_BRPOP_TIMEOUT_SECONDS",
        ),
    )
    knowledge_retrieval_default_limit: int = Field(
        default=8,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "KNOWLEDGE_RETRIEVAL_DEFAULT_LIMIT",
            "APP_KNOWLEDGE_RETRIEVAL_DEFAULT_LIMIT",
        ),
        description="Default number of knowledge chunks returned per retrieval call.",
    )
    knowledge_retrieval_max_limit: int = Field(
        default=25,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "KNOWLEDGE_RETRIEVAL_MAX_LIMIT",
            "APP_KNOWLEDGE_RETRIEVAL_MAX_LIMIT",
        ),
        description="Hard cap on retrieval limit (API and service clamp to this).",
    )
    knowledge_context_default_max_chunks: int = Field(
        default=5,
        ge=1,
        le=256,
        validation_alias=AliasChoices(
            "KNOWLEDGE_CONTEXT_DEFAULT_MAX_CHUNKS",
            "APP_KNOWLEDGE_CONTEXT_DEFAULT_MAX_CHUNKS",
        ),
        description="Default max chunks passed to the model after retrieval (cost control).",
    )
    knowledge_context_default_max_estimated_tokens: int = Field(
        default=4000,
        ge=64,
        le=2_000_000,
        validation_alias=AliasChoices(
            "KNOWLEDGE_CONTEXT_DEFAULT_MAX_ESTIMATED_TOKENS",
            "APP_KNOWLEDGE_CONTEXT_DEFAULT_MAX_ESTIMATED_TOKENS",
        ),
        description="Default total estimated-token budget for selected context (sum across chunks).",
    )
    knowledge_context_max_chunks_ceiling: int = Field(
        default=32,
        ge=1,
        le=512,
        validation_alias=AliasChoices(
            "KNOWLEDGE_CONTEXT_MAX_CHUNKS_CEILING",
            "APP_KNOWLEDGE_CONTEXT_MAX_CHUNKS_CEILING",
        ),
        description="Hard ceiling for per-request max context chunks (API cannot exceed).",
    )
    knowledge_context_max_estimated_tokens_ceiling: int = Field(
        default=200_000,
        ge=256,
        le=4_000_000,
        validation_alias=AliasChoices(
            "KNOWLEDGE_CONTEXT_MAX_ESTIMATED_TOKENS_CEILING",
            "APP_KNOWLEDGE_CONTEXT_MAX_ESTIMATED_TOKENS_CEILING",
        ),
        description="Hard ceiling for per-request estimated-token budget (API cannot exceed).",
    )

    object_storage_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "S3_ENDPOINT_URL",
            "APP_S3_ENDPOINT_URL",
            "MINIO_ENDPOINT",
            "APP_OBJECT_STORAGE_ENDPOINT_URL",
        ),
    )
    object_storage_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "S3_BUCKET",
            "APP_S3_BUCKET",
            "OBJECT_STORAGE_BUCKET",
            "APP_OBJECT_STORAGE_BUCKET",
        ),
    )
    object_storage_access_key_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_ACCESS_KEY_ID",
            "APP_OBJECT_STORAGE_ACCESS_KEY_ID",
            "S3_ACCESS_KEY_ID",
        ),
    )
    object_storage_secret_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_SECRET_ACCESS_KEY",
            "APP_OBJECT_STORAGE_SECRET_ACCESS_KEY",
            "S3_SECRET_ACCESS_KEY",
        ),
    )
    object_storage_region: str = Field(
        default="us-east-1",
        min_length=1,
        max_length=64,
        validation_alias=AliasChoices("AWS_REGION", "APP_OBJECT_STORAGE_REGION", "S3_REGION"),
    )
    object_storage_addressing_style: Literal["path", "virtual"] = Field(
        default="path",
        validation_alias=AliasChoices("APP_OBJECT_STORAGE_ADDRESSING_STYLE", "S3_ADDRESSING_STYLE"),
    )

    @field_validator(
        "object_storage_endpoint_url",
        "object_storage_bucket",
        "object_storage_access_key_id",
        "object_storage_secret_access_key",
        mode="before",
    )
    @classmethod
    def strip_blank_object_storage_optional_str(cls, value: object) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @field_validator("object_storage_addressing_style", mode="before")
    @classmethod
    def normalize_object_storage_addressing_style(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "path"
        s = str(value).strip().lower()
        if s not in ("path", "virtual"):
            raise ValueError("object_storage_addressing_style must be 'path' or 'virtual'")
        return s

    @field_validator("gemini_api_base_url", mode="before")
    @classmethod
    def strip_gemini_base_url(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "https://generativelanguage.googleapis.com/v1beta"
        return str(value).strip().rstrip("/")

    @field_validator("jwt_algorithm")
    @classmethod
    def jwt_algorithm_must_be_hmac(cls, value: str) -> str:
        allowed = frozenset({"HS256", "HS384", "HS512"})
        v = str(value).strip().upper()
        if v not in allowed:
            raise ValueError(f"jwt_algorithm must be one of {sorted(allowed)}")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        from urllib.parse import urlparse

        default_pair = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        if value is None or value == "":
            return list(default_pair)
        if isinstance(value, list):
            out = [str(x).strip() for x in value if str(x).strip()]
            raw = out or list(default_pair)
        elif isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            raw = parts or list(default_pair)
        else:
            raise ValueError("cors_origins must be a comma-separated string or a list of strings")

        validated: list[str] = []
        for origin in raw:
            if origin == "*":
                validated.append(origin)
                continue
            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(
                    f"CORS origin {origin!r} must use http:// or https:// scheme"
                )
            if not parsed.hostname:
                raise ValueError(
                    f"CORS origin {origin!r} must include a hostname"
                )
            validated.append(origin.rstrip("/"))
        return validated

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> str:
        if value is None:
            return "INFO"
        s = str(value).strip().upper()
        if s == "WARN":
            s = "WARNING"
        if s == "FATAL":
            s = "CRITICAL"
        if s not in _ALLOWED_LOG_LEVELS:
            raise ValueError(
                f"log_level must be one of {sorted(_ALLOWED_LOG_LEVELS - {'WARN', 'FATAL'})}"
            )
        return s

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("environment must be a non-empty string")
        return str(value).strip().lower()

    @property
    def auth_cookie_secure_effective(self) -> bool:
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.environment in _STRICT_DEPLOY_ENVIRONMENTS

    @model_validator(mode="after")
    def validate_auth_cookie_cors(self) -> Settings:
        if self.auth_cookie_enabled:
            if not self.cors_allow_credentials:
                raise ValueError(
                    "APP_AUTH_COOKIE_ENABLED requires APP_CORS_ALLOW_CREDENTIALS=true "
                    "and explicit APP_CORS_ORIGINS (no wildcard) so browsers send cookies."
                )
            if any(o.strip() == "*" for o in self.cors_origins):
                raise ValueError(
                    "APP_AUTH_COOKIE_ENABLED cannot be used with CORS wildcard origin '*'; "
                    "list explicit frontend origins."
                )
            if self.auth_cookie_same_site.lower() == "none" and not self.auth_cookie_secure_effective:
                raise ValueError(
                    "SameSite=None requires Secure cookies; set APP_AUTH_COOKIE_SECURE=true "
                    "or use staging/production defaults."
                )
        return self

    @model_validator(mode="after")
    def validate_cors_wildcard_credentials(self) -> Settings:
        # A wildcard origin ('*') combined with credentials makes Starlette reflect the caller's
        # Origin back AND send Access-Control-Allow-Credentials: true — a complete CORS bypass that
        # lets ANY website issue credentialed cross-origin requests and read the responses. This
        # must be rejected in every auth mode, not only when cookie auth is enabled.
        if self.cors_allow_credentials and any(o.strip() == "*" for o in self.cors_origins):
            raise ValueError(
                "APP_CORS_ALLOW_CREDENTIALS=true cannot be combined with a wildcard CORS origin '*'. "
                "List explicit origins in APP_CORS_ORIGINS, or set APP_CORS_ALLOW_CREDENTIALS=false."
            )
        return self

    @model_validator(mode="after")
    def validate_production_constraints(self) -> Settings:
        env = self.environment
        if env in _STRICT_DEPLOY_ENVIRONMENTS:
            deploy = "staging or production"
            if not self.database_url:
                raise ValueError(
                    f"DATABASE_URL (or APP_DATABASE_URL) is required for {deploy} (APP_ENVIRONMENT={env!r})"
                )
            if self.reload:
                raise ValueError(f"APP_RELOAD must be false for {deploy} (APP_ENVIRONMENT={env!r})")
            if self.log_request_body:
                raise ValueError(
                    f"APP_LOG_REQUEST_BODY must be false for {deploy} (APP_ENVIRONMENT={env!r})"
                )
            if self.expose_error_details:
                raise ValueError(
                    f"APP_EXPOSE_ERROR_DETAILS must be false for {deploy} (APP_ENVIRONMENT={env!r})"
                )
            if not self.jwt_secret_key or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    f"JWT_SECRET_KEY (or APP_JWT_SECRET_KEY) is required for {deploy} "
                    f"and must be at least 32 characters (APP_ENVIRONMENT={env!r})"
                )
            if int(self.ai_daily_total_tokens_soft_cap_per_bot) <= 0:
                raise ValueError(
                    f"APP_AI_DAILY_TOTAL_TOKENS_SOFT_CAP_PER_BOT must be > 0 for {deploy} "
                    f"(uncapped AI usage is not allowed; APP_ENVIRONMENT={env!r})"
                )
            if int(self.ai_monthly_total_tokens_cap_per_owner) <= 0:
                raise ValueError(
                    f"APP_AI_MONTHLY_TOTAL_TOKENS_CAP_PER_OWNER must be > 0 for {deploy} "
                    f"(uncapped owner usage is not allowed; APP_ENVIRONMENT={env!r})"
                )
            tg = (self.telegram_token_fernet_key or "").strip()
            if not tg:
                raise ValueError(
                    f"APP_TELEGRAM_TOKEN_FERNET_KEY is required for {deploy} "
                    f"(Telegram at-rest secrets use a dedicated Fernet key, not JWT_SECRET_KEY; "
                    f"APP_ENVIRONMENT={env!r})"
                )
            from cryptography.fernet import Fernet

            try:
                Fernet(tg.encode("utf-8"))
            except ValueError as exc:
                raise ValueError(
                    f"APP_TELEGRAM_TOKEN_FERNET_KEY must be a valid urlsafe base64 Fernet key for {deploy} "
                    f"(generate: python -c \"from cryptography.fernet import Fernet; "
                    f"print(Fernet.generate_key().decode())\"; APP_ENVIRONMENT={env!r})"
                ) from exc

            for origin in self.cors_origins:
                if origin == "*":
                    continue
                if not origin.startswith("https://"):
                    raise ValueError(
                        f"CORS origin {origin!r} must use https:// in {deploy} "
                        f"(APP_ENVIRONMENT={env!r})"
                    )
        return self

    @model_validator(mode="after")
    def validate_optional_secret_formats(self) -> Settings:
        """
        In any environment: non-empty ``JWT_SECRET_KEY`` must meet minimum length; non-empty
        ``APP_TELEGRAM_TOKEN_FERNET_KEY`` must be a valid Fernet key. Catches typos early instead
        of 401/500 on first request.
        """
        jwt_k = (self.jwt_secret_key or "").strip()
        if jwt_k and len(jwt_k) < 32:
            raise ValueError(
                "JWT_SECRET_KEY (or APP_JWT_SECRET_KEY) must be at least 32 characters when set. "
                "Use one stable secret per deployment; mismatch between processes causes not_authenticated."
            )
        tg = (self.telegram_token_fernet_key or "").strip()
        if tg:
            from cryptography.fernet import Fernet

            try:
                Fernet(tg.encode("utf-8"))
            except ValueError as exc:
                raise ValueError(
                    "APP_TELEGRAM_TOKEN_FERNET_KEY must be a valid urlsafe base64 Fernet key "
                    '(generate: python -c "from cryptography.fernet import Fernet; '
                    'print(Fernet.generate_key().decode())").'
                ) from exc
        env = str(self.environment).strip().lower()
        if env not in _STRICT_DEPLOY_ENVIRONMENTS and not tg:
            _LOG.info(
                "telegram_fernet_key_unset",
                environment=env,
                hint="Telegram connect returns 503 telegram_fernet_key_not_configured until key is set",
            )
        return self

    @property
    def deploy_environment_is_strict(self) -> bool:
        return str(self.environment).strip().lower() in _STRICT_DEPLOY_ENVIRONMENTS

    @property
    def public_widget_deny_empty_origin_allowlist_effective(self) -> bool:
        if self.deploy_environment_is_strict:
            return not self.public_widget_allow_empty_origin_allowlist
        return self.public_widget_force_deny_empty_origin_allowlist

    @property
    def public_widget_allow_allowlist_wildcard_patterns_effective(self) -> bool:
        if self.public_widget_allow_allowlist_wildcard_patterns is not None:
            return bool(self.public_widget_allow_allowlist_wildcard_patterns)
        return not self.deploy_environment_is_strict

    @model_validator(mode="after")
    def warn_public_widget_unsafe_empty_allowlist(self) -> Settings:
        if self.deploy_environment_is_strict and self.public_widget_allow_empty_origin_allowlist:
            _LOG.warning(
                "public_widget_allow_empty_origin_allowlist_enabled",
                extra={"environment": self.environment},
            )
        return self

    @property
    def knowledge_ingestion_redis_url_effective(self) -> str | None:
        u = (self.knowledge_ingestion_redis_url or "").strip()
        if u:
            return u
        rl = (self.rate_limit_redis_url or "").strip()
        return rl or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
