"""Persistence models (ORM / document schemas)."""

from app.models.ai_foundation import AIUsageLog, Conversation, DailyAIUsageAggregate, Message
from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.bot import Bot
from app.models.conversation_flow import ConversationDetectedIntent, ConversationFlowState
from app.models.coupon import Coupon
from app.models.email_campaign import EmailCampaign
from app.models.enums import OAuthProvider, PlanSlug, SubscriptionStatus, UserRole
from app.models.feature_flag import FeatureFlag
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_file import KnowledgeFile
from app.models.lead import Lead
from app.models.lead_event import LeadEvent
from app.models.owner_notification import OwnerNotification
from app.models.refresh_session import RefreshSession
from app.models.subscription import Subscription
from app.models.support_ticket import SupportTicket
from app.models.telegram_config import TelegramConfig
from app.models.user import OAuthAccount, User
from app.models.user_totp import UserTotp
from app.models.webhook_log import WebhookLog
from app.models.widget_config import WidgetConfig, new_public_widget_key

__all__ = [
    "AIUsageLog",
    "Base",
    "AuditLog",
    "Bot",
    "Conversation",
    "ConversationDetectedIntent",
    "ConversationFlowState",
    "Coupon",
    "DailyAIUsageAggregate",
    "EmailCampaign",
    "FeatureFlag",
    "KnowledgeChunk",
    "KnowledgeFile",
    "Lead",
    "LeadEvent",
    "Message",
    "OAuthAccount",
    "OAuthProvider",
    "OwnerNotification",
    "PlanSlug",
    "RefreshSession",
    "Subscription",
    "SubscriptionStatus",
    "SupportTicket",
    "User",
    "UserRole",
    "UserTotp",
    "WebhookLog",
    "WidgetConfig",
    "new_public_widget_key",
    "TelegramConfig",
]
