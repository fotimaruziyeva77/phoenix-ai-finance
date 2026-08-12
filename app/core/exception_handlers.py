import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.core.config import get_settings
from app.core.error_response import ErrorInfo, StandardErrorResponse
from app.core.error_tracking import capture_exception, capture_message, report_server_mapped_error
from app.core.exceptions import DatabaseNotConfiguredError
from app.core.logging import get_logger
from app.core.public_widget_channel_events import (
    WIDGET_ERROR,
    emit_public_widget_channel_event,
    is_public_widget_chat_path,
    public_widget_key_digest_from_path,
)
from app.services.ai_exceptions import AIServiceHTTPError, AIServiceQuotaExceededError
from app.services.auth_exceptions import AuthServiceError
from app.services.billing_exceptions import BillingError
from app.services.bot_exceptions import BotServiceError
from app.services.knowledge_file_exceptions import KnowledgeFileServiceError
from app.services.lead_pipeline_exceptions import LeadPipelineServiceError
from app.services.public_widget_chat_exceptions import PublicWidgetChatError
from app.services.telegram_config_exceptions import TelegramConfigServiceError
from app.services.web_widget_session_exceptions import WebWidgetSessionError
from app.services.widget_bootstrap_exceptions import WidgetBootstrapError
from app.services.totp_service import TotpError
from app.services.widget_config_exceptions import WidgetConfigServiceError

_LOG = get_logger(__name__)

_GENERIC_CLIENT_MESSAGE = "Request could not be processed"


def _emit_public_widget_error_event(request: Request, *, error_code: str, http_status: int) -> None:
    digest = public_widget_key_digest_from_path(request.url.path)
    emit_public_widget_channel_event(
        event=WIDGET_ERROR,
        level="warning",
        widget_key_digest=digest,
        error_code=error_code,
        http_status=http_status,
    )


_GENERIC_SERVER_MESSAGE = "An unexpected error occurred"


def _request_id(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    return str(rid) if rid is not None else None


def _correlation_id(request: Request) -> str | None:
    cid = getattr(request.state, "correlation_id", None)
    return str(cid) if cid is not None else None


def _json_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: object | None = None,
    request_id_override: str | None = None,
    category: str | None = None,
    ai_category: str | None = None,
) -> JSONResponse:
    rid = request_id_override if request_id_override is not None else _request_id(request)
    body = StandardErrorResponse(
        error=ErrorInfo(
            code=code,
            message=message,
            request_id=rid,
            category=category,
            ai_category=ai_category,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body.model_dump(exclude_none=True)),
    )


def _http_detail_is_mapping(detail: object) -> bool:
    return isinstance(detail, (list, dict))


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
    elif _http_detail_is_mapping(exc.detail):
        message = _GENERIC_CLIENT_MESSAGE
    else:
        message = str(exc.detail) if exc.detail else _GENERIC_CLIENT_MESSAGE

    code = "http_error"
    category: str | None = None
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "unauthorized"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "forbidden"
    elif exc.status_code == HTTP_429_TOO_MANY_REQUESTS:
        code = "rate_limit_exceeded"
        if request.url.path.startswith("/api/v1/auth"):
            category = "authentication"
        else:
            category = None

    response = _json_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request=request,
        details=exc.detail if _http_detail_is_mapping(exc.detail) else None,
        category=category,
    )
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="http",
            status_code=exc.status_code,
            code=code,
            exc=exc,
        )
    extra = getattr(exc, "headers", None)
    if extra:
        for hk, hv in extra.items():
            response.headers[hk] = hv
    return response


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _json_response(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message="Request validation failed",
        request=request,
        details=jsonable_encoder(exc.errors()),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id(request) or str(uuid.uuid4())
    _LOG.exception(
        "unhandled_exception",
        request_id=rid,
        correlation_id=_correlation_id(request),
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )
    capture_exception(exc, domain="unhandled", request=request)

    settings = get_settings()
    details = None
    if settings.expose_error_details and settings.environment not in (
        "production",
        "prod",
    ):
        details = {"type": type(exc).__name__}

    return _json_response(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message=_GENERIC_SERVER_MESSAGE,
        request=request,
        details=details,
        request_id_override=_request_id(request) or rid,
    )


async def billing_error_handler(
    request: Request,
    exc: BillingError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="billing",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="billing",
    )


async def auth_service_error_handler(
    request: Request,
    exc: AuthServiceError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="auth",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="authentication",
    )


async def bot_service_error_handler(
    request: Request,
    exc: BotServiceError,
) -> JSONResponse:
    cause = exc.__cause__
    if cause is not None:
        _LOG.warning(
            "bot_service_domain_error",
            code=exc.code,
            http_status=exc.status_code,
            cause_type=type(cause).__name__,
            request_id=_request_id(request),
        )
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="bots",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="bots",
    )


async def lead_pipeline_service_error_handler(
    request: Request,
    exc: LeadPipelineServiceError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="leads",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="leads",
    )


async def widget_config_service_error_handler(
    request: Request,
    exc: WidgetConfigServiceError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="widget",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="widget",
    )


async def telegram_config_service_error_handler(
    request: Request,
    exc: TelegramConfigServiceError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="telegram",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="telegram",
    )


async def widget_bootstrap_error_handler(
    request: Request,
    exc: WidgetBootstrapError,
) -> JSONResponse:
    _emit_public_widget_error_event(
        request,
        error_code=exc.code,
        http_status=exc.status_code,
    )
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="widget_public",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="widget_public",
    )


async def web_widget_session_error_handler(
    request: Request,
    exc: WebWidgetSessionError,
) -> JSONResponse:
    if is_public_widget_chat_path(request.url.path):
        _emit_public_widget_error_event(
            request,
            error_code=exc.code,
            http_status=exc.status_code,
        )
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="widget_session",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="widget_session",
    )


async def public_widget_chat_error_handler(
    request: Request,
    exc: PublicWidgetChatError,
) -> JSONResponse:
    _emit_public_widget_error_event(
        request,
        error_code=exc.code,
        http_status=exc.status_code,
    )
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="widget_public_chat",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="widget_public_chat",
    )


async def knowledge_file_service_error_handler(
    request: Request,
    exc: KnowledgeFileServiceError,
) -> JSONResponse:
    if exc.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="knowledge",
            status_code=exc.status_code,
            code=exc.code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        details=exc.details,
        category="knowledge",
    )


async def ai_service_http_error_handler(
    request: Request,
    exc: AIServiceHTTPError,
) -> JSONResponse:
    if is_public_widget_chat_path(request.url.path):
        if isinstance(exc, AIServiceQuotaExceededError):
            digest_q = public_widget_key_digest_from_path(request.url.path)
            emit_public_widget_channel_event(
                event=WIDGET_ERROR,
                level="warning",
                widget_key_digest=digest_q,
                error_code="public_widget_quota_sanitized",
                http_status=HTTP_503_SERVICE_UNAVAILABLE,
                extra=None,
            )
            return _json_response(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                code="public_widget_chat_unavailable",
                message="Service temporarily unavailable.",
                request=request,
                details=None,
                category="public_widget",
            )
        extra = {"ai_category": exc.ai_category} if exc.ai_category else None
        digest = public_widget_key_digest_from_path(request.url.path)
        emit_public_widget_channel_event(
            event=WIDGET_ERROR,
            level="warning",
            widget_key_digest=digest,
            error_code=exc.client_code,
            http_status=exc.client_status_code,
            extra=extra,
        )
    if exc.client_status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        report_server_mapped_error(
            request=request,
            domain="ai_chat",
            status_code=exc.client_status_code,
            code=exc.client_code,
            exc=exc,
        )
    return _json_response(
        status_code=exc.client_status_code,
        code=exc.client_code,
        message=exc.message,
        request=request,
        details=exc.details,
        category="ai_chat",
        ai_category=exc.ai_category,
    )


async def database_not_configured_handler(
    request: Request,
    exc: DatabaseNotConfiguredError,
) -> JSONResponse:
    capture_message(
        "database_not_configured",
        domain="configuration",
        level="error",
        request=request,
        tags={"error_code": "database_not_configured"},
    )
    return _json_response(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        code="database_not_configured",
        message=str(exc),
        request=request,
        category="configuration",
    )


async def totp_error_handler(request: Request, exc: TotpError) -> JSONResponse:
    return _standard_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request=request,
        category="auth",
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(DatabaseNotConfiguredError, database_not_configured_handler)
    application.add_exception_handler(BillingError, billing_error_handler)
    application.add_exception_handler(AuthServiceError, auth_service_error_handler)
    application.add_exception_handler(BotServiceError, bot_service_error_handler)
    application.add_exception_handler(WidgetConfigServiceError, widget_config_service_error_handler)
    application.add_exception_handler(TelegramConfigServiceError, telegram_config_service_error_handler)
    application.add_exception_handler(WidgetBootstrapError, widget_bootstrap_error_handler)
    application.add_exception_handler(WebWidgetSessionError, web_widget_session_error_handler)
    application.add_exception_handler(PublicWidgetChatError, public_widget_chat_error_handler)
    application.add_exception_handler(KnowledgeFileServiceError, knowledge_file_service_error_handler)
    application.add_exception_handler(LeadPipelineServiceError, lead_pipeline_service_error_handler)
    application.add_exception_handler(AIServiceHTTPError, ai_service_http_error_handler)
    application.add_exception_handler(TotpError, totp_error_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
