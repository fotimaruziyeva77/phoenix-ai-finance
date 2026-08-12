from typing import Annotated, Literal
from uuid import UUID

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookies import access_cookie_value
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.redis_client import get_redis_client
from app.core.limiters.memory_sliding_window import InMemorySlidingWindowLimiter
from app.core.limiters.protocol import SlidingWindowLimiterPort
from app.core.logging import get_logger
from app.core.public_widget_abuse import enforce_public_widget_chat_turn, widget_key_digest
from app.core.public_widget_channel_events import (
    THROTTLE_RATE_LIMIT_BOOTSTRAP,
    THROTTLE_RATE_LIMIT_CHAT,
    WIDGET_THROTTLED,
    emit_public_widget_channel_event,
)
from app.core.widget_abuse_redis import RedisWidgetStreakTracker
from app.core.rbac import is_superadmin
from app.core.request_client import client_ip
from app.core.request_log_context import bind_user_id_for_request
from app.integrations.oauth_exchange_store import OAuthExchangeStore
from app.lib.widget_origin_policy import WidgetOriginPolicyOptions
from app.models.user import User
from app.repositories.ai_chat_repository import AIChatRepository
from app.repositories.ai_usage_aggregate_repository import AIUsageAggregateRepository
from app.repositories.abuse_detection_repository import AbuseDetectionRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.email_campaign_repository import EmailCampaignRepository
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.repositories.segment_analytics_repository import SegmentAnalyticsRepository
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.repositories.webhook_log_repository import WebhookLogRepository
from app.repositories.knowledge_file_repository import KnowledgeFileRepository
from app.repositories.lead_event_repository import LeadEventRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.refresh_session_repository import RefreshSessionRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.public_widget_chat import PublicWidgetChatRequest
from app.services.admin_moderation_service import AdminModerationService
from app.services.ai_service import AIService
from app.services.audit_service import AuditService
from app.api.auth_csrf import enforce_csrf_if_cookie_session
from app.services.auth_exceptions import AuthServiceError
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.email_service import EmailService
from app.services.email_token_service import EmailTokenService
from app.integrations.email.resend_client import ResendEmailClient
from app.services.bot_chat_test_service import BotChatTestService
from app.services.bot_knowledge_file_service import BotKnowledgeFileService
from app.services.bot_service import BotService
from app.services.github_oauth_service import GithubOAuthService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.knowledge_retrieval_service import KnowledgeRetrievalService
from app.services.lead_event_service import LeadEventService
from app.services.lead_pipeline_service import LeadPipelineService
from app.services.platform_admin_service import PlatformAdminService
from app.services.tenant_inspection_service import TenantInspectionService
from app.services.public_widget_chat_service import PublicWidgetChatService
from app.contracts.telegram_channel_provisioning import TelegramChannelProvisioningPort
from app.services.telegram_config_service import TelegramConfigService
from app.services.telegram_webhook_inbound_service import TelegramWebhookInboundService
from app.services.web_widget_session_service import WebWidgetSessionService
from app.services.totp_service import TotpService
from app.services.widget_bootstrap_service import WidgetBootstrapService
from app.services.widget_config_service import WidgetConfigService

_LOG = get_logger(__name__)


def _settings_provider() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(_settings_provider)]

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(session: DbSession) -> UserRepository:
    return UserRepository(session)


def get_bot_repository(session: DbSession) -> BotRepository:
    return BotRepository(session)


def get_lead_pipeline_service(session: DbSession) -> LeadPipelineService:
    lead_repo = LeadRepository(session)
    return LeadPipelineService(
        lead_repo,
        LeadEventService(LeadEventRepository(session)),
    )


LeadPipelineServiceDep = Annotated[LeadPipelineService, Depends(get_lead_pipeline_service)]


def get_platform_admin_repository(session: DbSession) -> PlatformAdminRepository:
    return PlatformAdminRepository(session)


PlatformAdminRepoDep = Annotated[PlatformAdminRepository, Depends(get_platform_admin_repository)]


def get_platform_admin_service(session: DbSession) -> PlatformAdminService:
    return PlatformAdminService(PlatformAdminRepository(session))


PlatformAdminServiceDep = Annotated[PlatformAdminService, Depends(get_platform_admin_service)]


def get_audit_log_repository(session: DbSession) -> AuditLogRepository:
    return AuditLogRepository(session)


AuditLogRepoDep = Annotated[AuditLogRepository, Depends(get_audit_log_repository)]


def get_feature_flag_repository(session: DbSession) -> FeatureFlagRepository:
    return FeatureFlagRepository(session)


FeatureFlagRepoDep = Annotated[FeatureFlagRepository, Depends(get_feature_flag_repository)]


def get_support_ticket_repository(session: DbSession) -> SupportTicketRepository:
    return SupportTicketRepository(session)


SupportTicketRepoDep = Annotated[SupportTicketRepository, Depends(get_support_ticket_repository)]


def get_coupon_repository(session: DbSession) -> CouponRepository:
    return CouponRepository(session)


CouponRepoDep = Annotated[CouponRepository, Depends(get_coupon_repository)]


def get_segment_analytics_repository(session: DbSession) -> SegmentAnalyticsRepository:
    return SegmentAnalyticsRepository(session)


SegmentAnalyticsRepoDep = Annotated[SegmentAnalyticsRepository, Depends(get_segment_analytics_repository)]


def get_abuse_detection_repository(session: DbSession) -> AbuseDetectionRepository:
    return AbuseDetectionRepository(session)


AbuseDetectionRepoDep = Annotated[AbuseDetectionRepository, Depends(get_abuse_detection_repository)]


def get_email_campaign_repository(session: DbSession) -> EmailCampaignRepository:
    return EmailCampaignRepository(session)


EmailCampaignRepoDep = Annotated[EmailCampaignRepository, Depends(get_email_campaign_repository)]


def get_webhook_log_repository(session: DbSession) -> WebhookLogRepository:
    return WebhookLogRepository(session)


WebhookLogRepoDep = Annotated[WebhookLogRepository, Depends(get_webhook_log_repository)]


def get_subscription_repository(session: DbSession) -> SubscriptionRepository:
    return SubscriptionRepository(session)


SubscriptionRepoDep = Annotated[SubscriptionRepository, Depends(get_subscription_repository)]


def get_tenant_inspection_service(session: DbSession) -> TenantInspectionService:
    repo = PlatformAdminRepository(session)
    return TenantInspectionService(
        session=session,
        repo=repo,
        audit=AuditService(session),
        views=PlatformAdminService(repo),
    )


TenantInspectionServiceDep = Annotated[TenantInspectionService, Depends(get_tenant_inspection_service)]


def get_admin_moderation_service(session: DbSession) -> AdminModerationService:
    repo = PlatformAdminRepository(session)
    return AdminModerationService(
        session,
        repo,
        AuditService(session),
        PlatformAdminService(repo),
    )


AdminModerationServiceDep = Annotated[AdminModerationService, Depends(get_admin_moderation_service)]


def get_email_service(settings: SettingsDep) -> EmailService:
    redis_client = get_redis_client()
    resend_client = ResendEmailClient(settings)
    token_service = EmailTokenService(redis_client)
    return EmailService(settings, resend_client, token_service)


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


def get_auth_service(
    session: DbSession,
    settings: SettingsDep,
    email_service: EmailServiceDep,
) -> AuthService:
    return AuthService(
        UserRepository(session),
        RefreshSessionRepository(session),
        settings,
        email_service=email_service,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_widget_config_service(session: DbSession, settings: SettingsDep) -> WidgetConfigService:
    return WidgetConfigService(session, BotRepository(session), settings)


WidgetConfigServiceDep = Annotated[WidgetConfigService, Depends(get_widget_config_service)]


def get_totp_service(session: DbSession, settings: SettingsDep) -> TotpService:
    return TotpService(session, settings)


TotpServiceDep = Annotated[TotpService, Depends(get_totp_service)]


def get_telegram_config_service(session: DbSession, settings: SettingsDep) -> TelegramConfigService:
    return TelegramConfigService(session, BotRepository(session), settings)


TelegramConfigServiceDep = Annotated[TelegramChannelProvisioningPort, Depends(get_telegram_config_service)]


def get_bot_service(
    session: DbSession,
    telegram_service: TelegramConfigServiceDep,
) -> BotService:
    return BotService(
        BotRepository(session),
        AuditService(session),
        telegram_service=telegram_service,
        db_session=session,
    )


BotServiceDep = Annotated[BotService, Depends(get_bot_service)]


def get_widget_bootstrap_service(session: DbSession, settings: SettingsDep) -> WidgetBootstrapService:
    return WidgetBootstrapService(
        session,
        origin_policy=WidgetOriginPolicyOptions(
            loopback_aliases_equivalent=settings.public_widget_origin_loopback_equivalent,
            deny_empty_allowlist=settings.public_widget_deny_empty_origin_allowlist_effective,
        ),
    )


WidgetBootstrapServiceDep = Annotated[WidgetBootstrapService, Depends(get_widget_bootstrap_service)]


def get_web_widget_session_service(session: DbSession) -> WebWidgetSessionService:
    return WebWidgetSessionService(AIChatRepository(session), BotRepository(session))


WebWidgetSessionServiceDep = Annotated[WebWidgetSessionService, Depends(get_web_widget_session_service)]


def get_bot_knowledge_file_service(
    session: DbSession,
    settings: SettingsDep,
) -> BotKnowledgeFileService:
    return BotKnowledgeFileService(
        BotRepository(session),
        KnowledgeFileRepository(session),
        settings,
    )


BotKnowledgeFileServiceDep = Annotated[BotKnowledgeFileService, Depends(get_bot_knowledge_file_service)]


def get_knowledge_retrieval_service(
    session: DbSession,
    settings: SettingsDep,
) -> KnowledgeRetrievalService:
    return KnowledgeRetrievalService(session, settings)


KnowledgeRetrievalServiceDep = Annotated[KnowledgeRetrievalService, Depends(get_knowledge_retrieval_service)]


def get_bot_chat_test_service(session: DbSession, settings: SettingsDep) -> BotChatTestService:
    bot_repo = BotRepository(session)
    chat_repo = AIChatRepository(session)
    k_files = KnowledgeFileRepository(session)
    k_retrieval = KnowledgeRetrievalService(session, settings)
    return BotChatTestService(
        bot_repo=bot_repo,
        chat_repo=chat_repo,
        ai_service=AIService(
            chat_repo,
            bot_repo,
            settings=settings,
            knowledge_retrieval=k_retrieval,
            knowledge_files=k_files,
            usage_quota_repo=AIUsageAggregateRepository(session),
        ),
    )


BotChatTestServiceDep = Annotated[BotChatTestService, Depends(get_bot_chat_test_service)]


def get_public_widget_chat_service(session: DbSession, settings: SettingsDep) -> PublicWidgetChatService:
    bot_repo = BotRepository(session)
    chat_repo = AIChatRepository(session)
    k_files = KnowledgeFileRepository(session)
    k_retrieval = KnowledgeRetrievalService(session, settings)
    return PublicWidgetChatService(
        chat_repo=chat_repo,
        bot_repo=bot_repo,
        user_repo=UserRepository(session),
        ai_service=AIService(
            chat_repo,
            bot_repo,
            settings=settings,
            knowledge_retrieval=k_retrieval,
            knowledge_files=k_files,
            usage_quota_repo=AIUsageAggregateRepository(session),
            email_service=get_email_service(settings),
        ),
        origin_policy=WidgetOriginPolicyOptions(
            loopback_aliases_equivalent=settings.public_widget_origin_loopback_equivalent,
            deny_empty_allowlist=settings.public_widget_deny_empty_origin_allowlist_effective,
        ),
        billing_service=BillingService(
            SubscriptionRepository(session),
            UserRepository(session),
            settings,
        ),
    )


PublicWidgetChatServiceDep = Annotated[PublicWidgetChatService, Depends(get_public_widget_chat_service)]


def get_telegram_webhook_inbound_service(session: DbSession, settings: SettingsDep) -> TelegramWebhookInboundService:
    bot_repo = BotRepository(session)
    chat_repo = AIChatRepository(session)
    k_files = KnowledgeFileRepository(session)
    k_retrieval = KnowledgeRetrievalService(session, settings)
    user_repo = UserRepository(session)
    return TelegramWebhookInboundService(
        chat_repo,
        user_repo,
        AIService(
            chat_repo,
            bot_repo,
            settings=settings,
            knowledge_retrieval=k_retrieval,
            knowledge_files=k_files,
            usage_quota_repo=AIUsageAggregateRepository(session),
            email_service=get_email_service(settings),
        ),
        settings,
        billing_service=BillingService(
            SubscriptionRepository(session),
            user_repo,
            settings,
        ),
    )


TelegramWebhookInboundServiceDep = Annotated[
    TelegramWebhookInboundService,
    Depends(get_telegram_webhook_inbound_service),
]


def get_billing_service(session: DbSession, settings: SettingsDep) -> BillingService:
    return BillingService(
        SubscriptionRepository(session),
        UserRepository(session),
        settings,
        redis_client=get_redis_client(),
    )


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]


def get_sliding_window_limiter(request: Request) -> SlidingWindowLimiterPort:
    lim = getattr(request.app.state, "sliding_limiter", None)
    if lim is not None:
        return lim
    return _memory_fallback_limiter()


_memory_fallback: InMemorySlidingWindowLimiter | None = None


def _memory_fallback_limiter() -> InMemorySlidingWindowLimiter:
    global _memory_fallback
    if _memory_fallback is None:
        _memory_fallback = InMemorySlidingWindowLimiter()
    return _memory_fallback


def get_widget_streak_tracker(request: Request) -> RedisWidgetStreakTracker | None:
    return getattr(request.app.state, "widget_streak_tracker", None)


def _retry_headers(retry_after_seconds: int | None) -> dict[str, str]:
    if retry_after_seconds is None or retry_after_seconds <= 0:
        return {"Retry-After": "60"}
    return {"Retry-After": str(max(1, int(retry_after_seconds)))}


async def _enforce_rate_limit(
    request: Request,
    settings: Settings,
    limiter: SlidingWindowLimiterPort,
    *,
    prefix: str,
    limit_per_minute: int,
    endpoint_scope: Literal["auth", "oauth", "knowledge"],
    detail: str = "Too many requests. Please try again shortly.",
) -> None:
    if not settings.rate_limiting_enabled or limit_per_minute <= 0:
        return
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for) or "unknown"
    key = f"{prefix}:{ip}"
    try:
        out = await limiter.consume(key, limit=limit_per_minute, window_seconds=60.0)
    except redis.RedisError:
        _LOG.warning(
            "rate_limit_redis_degraded",
            endpoint_scope=endpoint_scope,
            policy="fail_closed" if settings.rate_limit_auth_fail_closed_on_redis_error else "allow",
            metric_event="rate_limit_redis_failure",
        )
        if settings.rate_limit_auth_fail_closed_on_redis_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again shortly.",
            )
        return
    if out.allowed:
        return
    _LOG.info(
        "rate_limit_blocked",
        endpoint_scope=endpoint_scope,
        limiter_key_prefix=prefix,
        retry_after_seconds=out.retry_after_seconds,
        metric_event="rate_limit_exceeded",
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers=_retry_headers(out.retry_after_seconds),
    )


async def rate_limit_auth_login(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_login",
        limit_per_minute=settings.rate_limit_login_per_minute,
        endpoint_scope="auth",
        detail="Too many login attempts. Please try again shortly.",
    )


async def rate_limit_auth_register(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_register",
        limit_per_minute=settings.rate_limit_register_per_minute,
        endpoint_scope="auth",
        detail="Too many registration attempts. Please try again shortly.",
    )


async def rate_limit_auth_refresh(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_refresh",
        limit_per_minute=settings.rate_limit_refresh_per_minute,
        endpoint_scope="auth",
    )


async def rate_limit_auth_logout(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_logout",
        limit_per_minute=settings.rate_limit_logout_per_minute,
        endpoint_scope="auth",
    )


async def rate_limit_auth_forgot_password(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_forgot_pw",
        limit_per_minute=settings.rate_limit_forgot_password_per_minute,
        endpoint_scope="auth",
        detail="Too many password-reset requests. Please try again shortly.",
    )


async def rate_limit_auth_reset_password(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="auth_reset_pw",
        limit_per_minute=settings.rate_limit_reset_password_per_minute,
        endpoint_scope="auth",
        detail="Too many password-reset attempts. Please try again shortly.",
    )


async def _enforce_public_widget_rate_limit(
    request: Request,
    settings: Settings,
    limiter: SlidingWindowLimiterPort,
    *,
    prefix: str,
    limit_per_minute: int,
    throttle_kind: str,
    digest: str,
    detail: str,
) -> None:
    if not settings.rate_limiting_enabled or limit_per_minute <= 0:
        return
    ip = client_ip(request, trust_forwarded_for=settings.trust_forwarded_for) or "unknown"
    key = f"{prefix}:{digest}:{ip}"
    try:
        out = await limiter.consume(key, limit=limit_per_minute, window_seconds=60.0)
    except redis.RedisError:
        _LOG.warning(
            "rate_limit_redis_degraded",
            endpoint_scope="public_widget",
            policy="fail_open" if settings.rate_limit_public_fail_open_on_redis_error else "fail_closed",
            metric_event="rate_limit_redis_failure",
        )
        if settings.rate_limit_public_fail_open_on_redis_error:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again shortly.",
        )
    if out.allowed:
        return
    _LOG.info(
        "rate_limit_blocked",
        endpoint_scope="public_widget",
        limiter_key_prefix=prefix,
        retry_after_seconds=out.retry_after_seconds,
        metric_event="rate_limit_exceeded",
    )
    emit_public_widget_channel_event(
        event=WIDGET_THROTTLED,
        level="warning",
        widget_key_digest=digest,
        throttle_kind=throttle_kind,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers=_retry_headers(out.retry_after_seconds),
    )


async def rate_limit_public_widget_chat(
    request: Request,
    settings: SettingsDep,
    public_widget_key: str,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    digest = widget_key_digest(public_widget_key)
    await _enforce_public_widget_rate_limit(
        request,
        settings,
        limiter,
        prefix="pub_widget_chat",
        limit_per_minute=settings.rate_limit_public_widget_chat_per_minute,
        throttle_kind=THROTTLE_RATE_LIMIT_CHAT,
        digest=digest,
        detail="Too many messages. Please try again shortly.",
    )


async def rate_limit_public_widget_bootstrap(
    request: Request,
    settings: SettingsDep,
    public_widget_key: str,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    digest = widget_key_digest(public_widget_key)
    await _enforce_public_widget_rate_limit(
        request,
        settings,
        limiter,
        prefix="pub_widget_boot",
        limit_per_minute=settings.rate_limit_public_widget_bootstrap_per_minute,
        throttle_kind=THROTTLE_RATE_LIMIT_BOOTSTRAP,
        digest=digest,
        detail="Too many requests. Please try again shortly.",
    )


async def enforce_public_widget_chat_abuse(
    request: Request,
    settings: SettingsDep,
    public_widget_key: str,
    body: PublicWidgetChatRequest,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
    streak_tracker: Annotated[RedisWidgetStreakTracker | None, Depends(get_widget_streak_tracker)],
) -> None:
    await enforce_public_widget_chat_turn(
        request=request,
        settings=settings,
        public_widget_key=public_widget_key,
        message_text=body.message,
        visitor_session_key=body.visitor_session_key,
        limiter=limiter,
        streak_tracker=streak_tracker,
    )


async def rate_limit_telegram_webhook(
    request: Request,
    bot_id: UUID,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    if not settings.rate_limiting_enabled or settings.rate_limit_telegram_webhook_per_minute <= 0:
        return
    key = f"tg_wh:{bot_id}"
    try:
        out = await limiter.consume(
            key,
            limit=settings.rate_limit_telegram_webhook_per_minute,
            window_seconds=60.0,
        )
    except redis.RedisError:
        _LOG.warning(
            "rate_limit_redis_degraded",
            endpoint_scope="telegram_webhook",
            metric_event="rate_limit_redis_failure",
        )
        return
    if out.allowed:
        return
    _LOG.info(
        "rate_limit_blocked",
        endpoint_scope="telegram_webhook",
        limiter_key_prefix="tg_wh",
        bot_id=str(bot_id),
        retry_after_seconds=out.retry_after_seconds,
        metric_event="rate_limit_exceeded",
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests.",
        headers=_retry_headers(out.retry_after_seconds),
    )


async def rate_limit_oauth_google_start(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="oauth_start_google",
        limit_per_minute=settings.rate_limit_oauth_start_per_minute,
        endpoint_scope="oauth",
    )


async def rate_limit_oauth_github_start(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="oauth_start_github",
        limit_per_minute=settings.rate_limit_oauth_start_per_minute,
        endpoint_scope="oauth",
    )


async def rate_limit_oauth_google_callback(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="oauth_callback_google",
        limit_per_minute=settings.rate_limit_oauth_callback_per_minute,
        endpoint_scope="oauth",
    )


async def rate_limit_oauth_github_callback(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="oauth_callback_github",
        limit_per_minute=settings.rate_limit_oauth_callback_per_minute,
        endpoint_scope="oauth",
    )


async def rate_limit_oauth_exchange(
    request: Request,
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    await _enforce_rate_limit(
        request,
        settings,
        limiter,
        prefix="oauth_exchange",
        limit_per_minute=settings.rate_limit_oauth_exchange_per_minute,
        endpoint_scope="oauth",
    )


_oauth_exchange_store: OAuthExchangeStore | None = None


def get_oauth_exchange_store() -> OAuthExchangeStore:
    global _oauth_exchange_store
    if _oauth_exchange_store is None:
        _oauth_exchange_store = OAuthExchangeStore()
    return _oauth_exchange_store


def get_google_oauth_service(
    auth_service: AuthServiceDep,
    store: Annotated[OAuthExchangeStore, Depends(get_oauth_exchange_store)],
) -> GoogleOAuthService:
    return GoogleOAuthService(auth_service, store)


GoogleOAuthServiceDep = Annotated[GoogleOAuthService, Depends(get_google_oauth_service)]


def get_github_oauth_service(
    auth_service: AuthServiceDep,
    store: Annotated[OAuthExchangeStore, Depends(get_oauth_exchange_store)],
) -> GithubOAuthService:
    return GithubOAuthService(auth_service, store)


GithubOAuthServiceDep = Annotated[GithubOAuthService, Depends(get_github_oauth_service)]

_http_bearer_optional = HTTPBearer(auto_error=False)


def get_bearer_token_optional(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_http_bearer_optional),
    ],
) -> str | None:
    return credentials.credentials if credentials else None


def get_access_token_optional(
    request: Request,
    settings: SettingsDep,
    bearer: Annotated[str | None, Depends(get_bearer_token_optional)],
) -> str | None:
    """Bearer ``Authorization`` wins; otherwise HttpOnly access cookie when cookie auth is enabled."""
    if bearer:
        return bearer
    if settings.auth_cookie_enabled:
        v = access_cookie_value(request, settings)
        return v if v else None
    return None


async def require_csrf_if_cookie_auth(request: Request, settings: SettingsDep) -> None:
    enforce_csrf_if_cookie_session(request, settings)


async def get_current_user_optional(
    request: Request,
    auth_service: AuthServiceDep,
    token: Annotated[str | None, Depends(get_access_token_optional)],
) -> User | None:
    """Authenticated user, or ``None`` if missing/invalid token (no HTTP error)."""
    if token is None:
        return None
    try:
        user = await auth_service.get_user_for_access_token(token)
    except AuthServiceError:
        return None
    request.state.log_user_id = str(user.id)
    bind_user_id_for_request(user.id)
    return user


async def require_authenticated_user(
    request: Request,
    auth_service: AuthServiceDep,
    token: Annotated[str | None, Depends(get_access_token_optional)],
) -> User:
    """
    Valid access token and active user (any role).

    Owner-scoped routes should continue to enforce ``owner_id == user.id`` in services; assigning
    ``superadmin`` does not widen those queries unless an explicit admin handler is added.
    """
    user = await auth_service.get_user_for_access_token(token)
    request.state.log_user_id = str(user.id)
    bind_user_id_for_request(user.id)
    return user


# Backwards-compatible name used by existing dependencies and tests.
get_current_user_required = require_authenticated_user


async def require_superadmin(
    user: Annotated[User, Depends(require_authenticated_user)],
) -> User:
    """Require authenticated platform superadmin (403 if role is not ``superadmin``)."""
    if not is_superadmin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required.",
        )
    return user


async def rate_limit_billing_checkout(
    request: Request,
    settings: SettingsDep,
    user: Annotated[User, Depends(require_authenticated_user)],
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    """Per-user checkout throttle — max 5 requests per minute."""
    if not settings.rate_limiting_enabled:
        return
    key = f"billing_checkout:{user.id}"
    try:
        out = await limiter.consume(key, limit=5, window_seconds=60.0)
    except redis.RedisError:
        _LOG.warning(
            "rate_limit_redis_degraded",
            endpoint_scope="billing",
            policy="fail_closed" if settings.rate_limit_auth_fail_closed_on_redis_error else "allow",
            metric_event="rate_limit_redis_failure",
        )
        if settings.rate_limit_auth_fail_closed_on_redis_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again shortly.",
            )
        return
    if out.allowed:
        return
    _LOG.info(
        "rate_limit_blocked",
        endpoint_scope="billing",
        limiter_key_prefix="billing_checkout",
        retry_after_seconds=out.retry_after_seconds,
        metric_event="rate_limit_exceeded",
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many checkout requests. Please try again shortly.",
        headers=_retry_headers(out.retry_after_seconds),
    )


async def rate_limit_knowledge_upload(
    request: Request,
    bot_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    settings: SettingsDep,
    limiter: Annotated[SlidingWindowLimiterPort, Depends(get_sliding_window_limiter)],
) -> None:
    """Per-owner+per-bot upload throttle (Redis-backed when configured)."""
    if not settings.rate_limiting_enabled or settings.knowledge_upload_rate_limit_per_minute <= 0:
        return
    key = f"knowledge_upload:{user.id}:{bot_id}"
    try:
        out = await limiter.consume(
            key,
            limit=settings.knowledge_upload_rate_limit_per_minute,
            window_seconds=60.0,
        )
    except redis.RedisError:
        _LOG.warning(
            "rate_limit_redis_degraded",
            endpoint_scope="knowledge",
            policy="fail_closed" if settings.rate_limit_auth_fail_closed_on_redis_error else "allow",
            metric_event="rate_limit_redis_failure",
        )
        if settings.rate_limit_auth_fail_closed_on_redis_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again shortly.",
            )
        return
    if out.allowed:
        return
    _LOG.info(
        "rate_limit_blocked",
        endpoint_scope="knowledge",
        limiter_key_prefix="knowledge_upload",
        retry_after_seconds=out.retry_after_seconds,
        metric_event="rate_limit_exceeded",
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many knowledge uploads for this bot. Please try again shortly.",
        headers=_retry_headers(out.retry_after_seconds),
    )


CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentUser = Annotated[User, Depends(require_authenticated_user)]
RequireAuthenticatedUser = Annotated[User, Depends(require_authenticated_user)]
RequireSuperadmin = Annotated[User, Depends(require_superadmin)]
