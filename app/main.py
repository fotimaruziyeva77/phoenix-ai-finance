import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import dispose_engine, get_session_maker
from app.core.limiters.factory import attach_sliding_window_limiter
from app.core.redis_client import close_redis_client, init_redis_client
from app.core.widget_abuse_redis import RedisWidgetStreakTracker
from app.core.error_tracking import init_error_tracking, shutdown_error_tracking
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.timeout_middleware import RequestTimeoutMiddleware


async def _startup_telegram_webhook_resync(log, settings) -> None:  # noqa: ANN001
    """Best-effort background task: re-register Telegram webhooks after restart."""
    if not getattr(settings, "public_api_base_url", None):
        log.info("telegram_startup_resync_skipped", reason="APP_PUBLIC_API_BASE_URL not set")
        return
    try:
        from sqlalchemy import select  # noqa: PLC0415
        from app.models.telegram_config import TelegramConfig  # noqa: PLC0415
        from app.models.bot import Bot  # noqa: PLC0415
        from app.domain.telegram_channel_status import TELEGRAM_PROVISIONING_ACTIVE  # noqa: PLC0415
        from app.integrations.telegram_webhook_registration import set_telegram_bot_webhook  # noqa: PLC0415
        from app.integrations.telegram_webhook_urls import build_telegram_webhook_url  # noqa: PLC0415
        from app.lib.telegram_token_crypto import decrypt_telegram_bot_token  # noqa: PLC0415

        session_maker = get_session_maker()
        async with session_maker() as session:
            stmt = (
                select(TelegramConfig)
                .join(Bot, Bot.id == TelegramConfig.bot_id)
                .where(
                    TelegramConfig.is_connected.is_(True),
                    TelegramConfig.provisioning_status == TELEGRAM_PROVISIONING_ACTIVE,
                    Bot.status != "archived",
                    TelegramConfig.bot_token_encrypted.isnot(None),
                    TelegramConfig.bot_token_encrypted != "",
                )
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                log.info("telegram_startup_resync_skipped", reason="no connected bots")
                return
            succeeded, failed = 0, 0
            for cfg in rows:
                try:
                    token = decrypt_telegram_bot_token(cfg.bot_token_encrypted, settings)
                    webhook_url = build_telegram_webhook_url(settings.public_api_base_url, cfg.bot_id)
                    wh_secret = decrypt_telegram_bot_token(cfg.webhook_secret_token_encrypted, settings) if cfg.webhook_secret_token_encrypted else ""
                    await set_telegram_bot_webhook(
                        bot_token=token,
                        webhook_https_url=webhook_url,
                        secret_token=wh_secret,
                    )
                    succeeded += 1
                except Exception:
                    failed += 1
            log.info(
                "telegram_startup_resync_complete",
                total=len(rows),
                succeeded=succeeded,
                failed=failed,
            )
    except Exception as exc:
        log.warning("telegram_startup_resync_error", exc_type=type(exc).__name__, error=str(exc)[:200])


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_logger(__name__)
    settings = get_settings()
    init_error_tracking(settings)
    redis_c = await init_redis_client(settings)
    attach_sliding_window_limiter(app, settings)
    if redis_c is not None:
        pfx = settings.rate_limit_redis_key_prefix.rstrip(":")
        app.state.widget_streak_tracker = RedisWidgetStreakTracker(
            redis_c,
            key_prefix=f"{pfx}:wg:str:",
        )
    else:
        app.state.widget_streak_tracker = None
    log.info("application_startup", env=settings.environment, rate_limit_redis=bool(redis_c))
    # Log OAuth redirect URIs at startup so mismatches are visible immediately.
    log.info(
        "oauth_config_summary",
        google_oauth_redirect_uri=settings.google_oauth_redirect_uri or "(not set)",
        github_oauth_redirect_uri=settings.github_oauth_redirect_uri or "(not set)",
        frontend_oauth_redirect_url=settings.frontend_oauth_redirect_url or "(not set)",
    )
    # Best-effort: resync all connected Telegram webhooks with current public API URL.
    asyncio.create_task(_startup_telegram_webhook_resync(log, settings))
    yield
    shutdown_error_tracking()
    log.info("application_shutdown")
    await close_redis_client()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.log_json,
        service_name=settings.service_name,
        environment=settings.environment,
        suppress_uvicorn_access=not settings.use_uvicorn_access_log,
    )
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.expose_docs else None,
        redoc_url="/redoc" if settings.expose_docs else None,
        openapi_url="/openapi.json" if settings.expose_docs else None,
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    # Middleware execution order: outermost (added last) runs first.
    # CORS → SecurityHeaders → Timeout → Logging → route handler
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestTimeoutMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-Correlation-ID",
            "X-Request-ID",
            "ngrok-skip-browser-warning",
        ],
        expose_headers=["X-Request-Id"],
    )
    application.include_router(api_router)
    return application


app = create_app()
