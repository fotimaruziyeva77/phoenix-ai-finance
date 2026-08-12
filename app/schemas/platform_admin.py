"""Superadmin platform overview API shapes (no secrets, no ORM leakage)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OAuthProvider, UserRole


class AdminOAuthProviderBrief(BaseModel):
    """Linked OAuth identity (no provider_user_id / tokens)."""

    provider: OAuthProvider


class AdminUserListItem(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    suspended_at: datetime | None
    has_password: bool
    oauth_provider_count: int = Field(ge=0, description="Number of linked OAuth accounts.")
    bot_count: int = Field(ge=0, description="Bots owned by this user.")
    created_at: datetime
    updated_at: datetime


class AdminUserDetail(AdminUserListItem):
    suspension_reason: str | None = Field(
        default=None,
        description="Internal moderation note (superadmin only).",
    )
    oauth_providers: list[AdminOAuthProviderBrief] = Field(default_factory=list)


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class AdminBotListItem(BaseModel):
    id: UUID
    owner_id: UUID
    owner_email: str
    name: str
    niche_id: str
    goal_type: str
    status: str
    provider_name: str
    model_name: str | None
    widget_configured: bool = Field(description="At least one widget config row exists for this bot.")
    telegram_connected: bool = Field(description="Telegram integration row exists and is_connected.")
    platform_suspended_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminBotDetail(AdminBotListItem):
    platform_suspension_reason: str | None = None
    welcome_message: str | None = None
    tone: str | None = None
    language: str | None = None
    short_description: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None


class AdminBotListResponse(BaseModel):
    items: list[AdminBotListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class AdminTenantChannelSummaryItem(BaseModel):
    channel: str = Field(description="Conversation ingress key; 'legacy' when channel was unset.")
    conversation_count: int = Field(ge=0)


class AdminTenantAIUsageWindowSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_calls: int = Field(ge=0)
    successful_calls: int = Field(ge=0)
    failed_calls: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class AdminTenantDailyAIUsageRow(BaseModel):
    usage_date: date
    total_requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0, description="Summed platform cost for the day (USD).")


class AdminTenantRecentAIFailure(BaseModel):
    at: datetime
    bot_id: UUID
    model_name: str
    error_code: str | None = None


class AdminSubscriptionDistributionItem(BaseModel):
    plan_slug: str
    count: int = Field(ge=0)


class AdminPlatformStatsResponse(BaseModel):
    """High-level platform health snapshot (superadmin only)."""

    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    total_bots: int = Field(ge=0)
    active_bots: int = Field(ge=0)
    total_leads: int = Field(ge=0)
    total_conversations: int = Field(ge=0)
    subscription_distribution: list[AdminSubscriptionDistributionItem] = Field(default_factory=list)
    # Billing KPIs
    mrr_usd: float = Field(default=0.0, description="Monthly Recurring Revenue.")
    total_paid_active: int = Field(default=0, ge=0)
    total_free: int = Field(default=0, ge=0)
    total_past_due: int = Field(default=0, ge=0)
    total_canceled: int = Field(default=0, ge=0)
    generated_at: datetime


class AdminBillingListItem(BaseModel):
    """Subscription row joined with user info for billing management."""
    user_id: UUID
    user_email: str
    user_full_name: str | None
    user_is_active: bool
    plan_slug: str
    status: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    canceled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminBillingListResponse(BaseModel):
    items: list[AdminBillingListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class AdminBillingStats(BaseModel):
    """Billing KPIs for the overview dashboard."""
    mrr_usd: float = Field(description="Monthly Recurring Revenue (active paid plans only).")
    total_paid_active: int = Field(ge=0, description="Users on a paid plan with active status.")
    total_free: int = Field(ge=0)
    total_past_due: int = Field(ge=0)
    total_canceled: int = Field(ge=0)
    total_expired: int = Field(ge=0)
    plan_distribution: list[AdminSubscriptionDistributionItem] = Field(default_factory=list)


class AdminSubscriptionOverrideBody(BaseModel):
    """Request body for superadmin manual plan override."""

    model_config = ConfigDict(extra="forbid")

    plan_slug: str = Field(..., description="Target plan slug (e.g. 'free', 'pro', 'business').")
    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Internal note explaining why the override was applied.",
    )


class AdminSubscriptionRead(BaseModel):
    """Current subscription row after an admin override."""

    user_id: UUID
    plan_slug: str
    status: str
    updated_at: datetime


# ── Audit Log ──────────────────────────────────────────────────────────────

class AdminAuditLogItem(BaseModel):
    """Single audit event row with actor email resolved."""

    id: UUID
    actor_user_id: UUID
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: UUID
    before_snapshot: dict | None = None
    after_snapshot: dict | None = None
    metadata_json: dict | None = None
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class AdminAuditLogMetaResponse(BaseModel):
    """Distinct values for filter dropdowns."""
    actions: list[str]
    entity_types: list[str]


# ── AI Usage Monitor ────────────────────────────────────────────────────────

class AdminAIUsagePlatformStats(BaseModel):
    """Platform-wide AI call totals for the requested period."""

    period_days: int = Field(ge=1)
    total_calls: int = Field(ge=0)
    successful_calls: int = Field(ge=0)
    failed_calls: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    success_rate: float = Field(ge=0, le=1, description="0.0–1.0")


class AdminAIUsageDailyRow(BaseModel):
    usage_date: date
    total_requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0)


class AdminAIUsageTopConsumer(BaseModel):
    owner_id: UUID
    owner_email: str
    total_tokens: int = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    total_calls: int = Field(ge=0)


class AdminAIUsageResponse(BaseModel):
    stats: AdminAIUsagePlatformStats
    daily: list[AdminAIUsageDailyRow]
    top_consumers: list[AdminAIUsageTopConsumer]


# ───────────────────────────────────────────────────────────────────────────

class AdminTenantInspectionResponse(BaseModel):
    """
    Read-only operational snapshot for a tenant (owner user).
    Returned only to superadmin; each successful fetch is audit-logged.
    """

    tenant_user_id: UUID
    summary: AdminUserDetail
    bots: list[AdminBotListItem]
    channels: list[AdminTenantChannelSummaryItem]
    lead_count: int = Field(ge=0)
    conversation_count: int = Field(ge=0)
    ai_usage: AdminTenantAIUsageWindowSummary
    ai_daily_usage: list[AdminTenantDailyAIUsageRow]
    recent_ai_failures: list[AdminTenantRecentAIFailure]
