"""Aggregates versioned HTTP routers (handlers stay thin; call services)."""

from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_v1_router
from app.api.v1.admin_abuse import router as admin_abuse_v1_router
from app.api.v1.admin_bulk_actions import router as admin_bulk_actions_v1_router
from app.api.v1.admin_campaigns import router as admin_campaigns_v1_router
from app.api.v1.admin_coupons import router as admin_coupons_v1_router
from app.api.v1.admin_export import router as admin_export_v1_router
from app.api.v1.admin_feature_flags import router as admin_feature_flags_v1_router
from app.api.v1.admin_impersonation import router as admin_impersonation_v1_router
from app.api.v1.admin_moderation import router as admin_moderation_v1_router
from app.api.v1.admin_segment_analytics import router as admin_segment_analytics_v1_router
from app.api.v1.admin_support import router as admin_support_v1_router
from app.api.v1.admin_webhook_logs import router as admin_webhook_logs_v1_router
from app.api.v1.admin_overview import router as admin_overview_v1_router
from app.api.v1.admin_tenant_inspection import router as admin_tenant_inspection_v1_router
from app.api.v1.admin_platform import router as admin_platform_v1_router
from app.api.v1.auth import router as auth_v1_router
from app.api.v1.auth_2fa import router as auth_2fa_v1_router
from app.api.v1.billing import router as billing_v1_router
from app.api.v1.bot_chat import router as bot_chat_v1_router
from app.api.v1.bot_knowledge_files import router as bot_knowledge_files_v1_router
from app.api.v1.bot_knowledge_retrieval import router as bot_knowledge_retrieval_v1_router
from app.api.v1.bot_telegram import router as bot_telegram_v1_router
from app.api.v1.bot_widget import router as bot_widget_v1_router
from app.api.v1.bots import router as bots_v1_router
from app.api.v1.finance import router as finance_v1_router
from app.api.v1.github_oauth import router as github_oauth_v1_router
from app.api.v1.google_oauth import router as google_oauth_v1_router
from app.api.v1.health import router as health_v1_router
from app.api.v1.leads import router as leads_v1_router
from app.api.v1.niche_catalog import router as niche_catalog_v1_router
from app.api.v1.notifications import router as notifications_v1_router
from app.api.v1.telegram_linking import router as telegram_linking_v1_router
from app.api.v1.oauth_exchange import router as oauth_exchange_v1_router
from app.api.v1.public_telegram import router as public_telegram_v1_router
from app.api.v1.public_widget import router as public_widget_v1_router
from app.api.v1.support import router as support_v1_router

api_router = APIRouter()
api_router.include_router(health_v1_router, prefix="/api/v1")
api_router.include_router(niche_catalog_v1_router, prefix="/api/v1")
api_router.include_router(finance_v1_router, prefix="/api/v1")
api_router.include_router(admin_overview_v1_router, prefix="/api/v1")
api_router.include_router(admin_feature_flags_v1_router, prefix="/api/v1")
api_router.include_router(admin_abuse_v1_router, prefix="/api/v1")
api_router.include_router(admin_bulk_actions_v1_router, prefix="/api/v1")
api_router.include_router(admin_campaigns_v1_router, prefix="/api/v1")
api_router.include_router(admin_coupons_v1_router, prefix="/api/v1")
api_router.include_router(admin_export_v1_router, prefix="/api/v1")
api_router.include_router(admin_impersonation_v1_router, prefix="/api/v1")
api_router.include_router(admin_segment_analytics_v1_router, prefix="/api/v1")
api_router.include_router(admin_support_v1_router, prefix="/api/v1")
api_router.include_router(admin_webhook_logs_v1_router, prefix="/api/v1")
api_router.include_router(admin_tenant_inspection_v1_router, prefix="/api/v1")
api_router.include_router(admin_moderation_v1_router, prefix="/api/v1")
api_router.include_router(admin_platform_v1_router, prefix="/api/v1")
api_router.include_router(support_v1_router, prefix="/api/v1")
api_router.include_router(public_widget_v1_router, prefix="/api/v1")
api_router.include_router(public_telegram_v1_router, prefix="/api/v1")
api_router.include_router(bots_v1_router, prefix="/api/v1")
api_router.include_router(bot_widget_v1_router, prefix="/api/v1")
api_router.include_router(bot_telegram_v1_router, prefix="/api/v1")
api_router.include_router(bot_knowledge_files_v1_router, prefix="/api/v1")
api_router.include_router(bot_knowledge_retrieval_v1_router, prefix="/api/v1")
api_router.include_router(leads_v1_router, prefix="/api/v1")
api_router.include_router(notifications_v1_router, prefix="/api/v1")
api_router.include_router(telegram_linking_v1_router, prefix="/api/v1")
api_router.include_router(bot_chat_v1_router, prefix="/api/v1")
api_router.include_router(billing_v1_router, prefix="/api/v1")
api_router.include_router(analytics_v1_router, prefix="/api/v1")
api_router.include_router(auth_v1_router, prefix="/api/v1/auth")
api_router.include_router(auth_2fa_v1_router, prefix="/api/v1/auth")
api_router.include_router(oauth_exchange_v1_router, prefix="/api/v1/auth")
api_router.include_router(google_oauth_v1_router, prefix="/api/v1/auth")
api_router.include_router(github_oauth_v1_router, prefix="/api/v1/auth")
