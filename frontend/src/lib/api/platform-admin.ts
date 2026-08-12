import { apiFetchWithAuth } from "@/lib/api/client";

/** Shapes match FastAPI ``platform_admin`` / ``admin_moderation`` responses (snake_case). */

export type AdminOAuthProviderBriefDto = {
  provider: string;
};

export type AdminUserListItemDto = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  suspended_at: string | null;
  has_password: boolean;
  oauth_provider_count: number;
  bot_count: number;
  created_at: string;
  updated_at: string;
};

export type AdminUserDetailDto = AdminUserListItemDto & {
  suspension_reason: string | null;
  oauth_providers: AdminOAuthProviderBriefDto[];
};

export type AdminUserListResponseDto = {
  items: AdminUserListItemDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminBotListItemDto = {
  id: string;
  owner_id: string;
  owner_email: string;
  name: string;
  niche_id: string;
  goal_type: string;
  status: string;
  provider_name: string;
  model_name: string | null;
  widget_configured: boolean;
  telegram_connected: boolean;
  platform_suspended_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminBotDetailDto = AdminBotListItemDto & {
  platform_suspension_reason: string | null;
  welcome_message: string | null;
  tone: string | null;
  language: string | null;
  short_description: string | null;
  temperature: number | null;
  max_output_tokens: number | null;
};

export type AdminBotListResponseDto = {
  items: AdminBotListItemDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminTenantChannelSummaryDto = {
  channel: string;
  conversation_count: number;
};

export type AdminTenantAIUsageWindowDto = {
  period_start: string;
  period_end: string;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_tokens: number;
};

export type AdminTenantDailyAIUsageRowDto = {
  usage_date: string;
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
};

export type AdminTenantRecentAIFailureDto = {
  at: string;
  bot_id: string;
  model_name: string;
  error_code: string | null;
};

/** Read-only superadmin tenant diagnostics (each load is audit-logged server-side). */
export type AdminTenantInspectionDto = {
  tenant_user_id: string;
  summary: AdminUserDetailDto;
  bots: AdminBotListItemDto[];
  channels: AdminTenantChannelSummaryDto[];
  lead_count: number;
  conversation_count: number;
  ai_usage: AdminTenantAIUsageWindowDto;
  ai_daily_usage: AdminTenantDailyAIUsageRowDto[];
  recent_ai_failures: AdminTenantRecentAIFailureDto[];
};

export type ListUsersParams = {
  limit?: number;
  offset?: number;
  role?: string;
  is_active?: boolean;
  search?: string;
};

export type ListBotsParams = {
  limit?: number;
  offset?: number;
  owner_id?: string;
  niche_id?: string;
  status?: string;
  has_widget?: boolean;
  has_telegram_connected?: boolean;
  platform_suspended?: boolean;
  search?: string;
};

function withQuery(path: string, params: Record<string, string | number | boolean | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue;
    sp.set(k, String(v));
  }
  const q = sp.toString();
  return q ? `${path}?${q}` : path;
}

export async function listAdminUsers(
  accessToken: string | null,
  params: ListUsersParams = {},
): Promise<AdminUserListResponseDto> {
  const path = withQuery("/api/v1/admin/users", {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    role: params.role,
    is_active: params.is_active,
    search: params.search,
  });
  return apiFetchWithAuth<AdminUserListResponseDto>(path, accessToken, { method: "GET" });
}

export async function getAdminUser(accessToken: string | null, userId: string): Promise<AdminUserDetailDto> {
  return apiFetchWithAuth<AdminUserDetailDto>(`/api/v1/admin/users/${userId}`, accessToken, { method: "GET" });
}

export async function listAdminBots(
  accessToken: string | null,
  params: ListBotsParams = {},
): Promise<AdminBotListResponseDto> {
  const path = withQuery("/api/v1/admin/bots", {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    owner_id: params.owner_id,
    niche_id: params.niche_id,
    status: params.status,
    has_widget: params.has_widget,
    has_telegram_connected: params.has_telegram_connected,
    platform_suspended: params.platform_suspended,
    search: params.search,
  });
  return apiFetchWithAuth<AdminBotListResponseDto>(path, accessToken, { method: "GET" });
}

export async function getAdminBot(accessToken: string | null, botId: string): Promise<AdminBotDetailDto> {
  return apiFetchWithAuth<AdminBotDetailDto>(`/api/v1/admin/bots/${botId}`, accessToken, { method: "GET" });
}

export async function fetchTenantInspection(
  accessToken: string | null,
  ownerUserId: string,
): Promise<AdminTenantInspectionDto> {
  return apiFetchWithAuth<AdminTenantInspectionDto>(
    `/api/v1/admin/tenants/${ownerUserId}/inspection`,
    accessToken,
    { method: "GET" },
  );
}

export async function suspendAdminUser(
  accessToken: string | null,
  userId: string,
  body: { reason?: string | null },
): Promise<AdminUserDetailDto> {
  return apiFetchWithAuth<AdminUserDetailDto>(`/api/v1/admin/users/${userId}/suspend`, accessToken, {
    method: "POST",
    body,
  });
}

export async function activateAdminUser(accessToken: string | null, userId: string): Promise<AdminUserDetailDto> {
  return apiFetchWithAuth<AdminUserDetailDto>(`/api/v1/admin/users/${userId}/activate`, accessToken, {
    method: "POST",
    body: {},
  });
}

export async function suspendAdminBot(
  accessToken: string | null,
  botId: string,
  body: { reason?: string | null },
): Promise<AdminBotDetailDto> {
  return apiFetchWithAuth<AdminBotDetailDto>(`/api/v1/admin/bots/${botId}/suspend`, accessToken, {
    method: "POST",
    body,
  });
}

export async function activateAdminBot(accessToken: string | null, botId: string): Promise<AdminBotDetailDto> {
  return apiFetchWithAuth<AdminBotDetailDto>(`/api/v1/admin/bots/${botId}/activate`, accessToken, {
    method: "POST",
    body: {},
  });
}

// ── Billing ────────────────────────────────────────────────────────────────

export type AdminBillingListItemDto = {
  user_id: string;
  user_email: string;
  user_full_name: string | null;
  user_is_active: boolean;
  plan_slug: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  canceled_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminBillingListResponseDto = {
  items: AdminBillingListItemDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminPlatformStatsDto = {
  total_users: number;
  active_users: number;
  total_bots: number;
  active_bots: number;
  total_leads: number;
  total_conversations: number;
  subscription_distribution: { plan_slug: string; count: number }[];
  mrr_usd: number;
  total_paid_active: number;
  total_free: number;
  total_past_due: number;
  total_canceled: number;
  generated_at: string;
};

export type ListBillingParams = {
  limit?: number;
  offset?: number;
  status?: string;
  plan_slug?: string;
};

export async function listAdminBilling(
  accessToken: string | null,
  params: ListBillingParams = {},
): Promise<AdminBillingListResponseDto> {
  const path = withQuery("/api/v1/admin/billing/subscriptions", {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    status: params.status,
    plan_slug: params.plan_slug,
  });
  return apiFetchWithAuth<AdminBillingListResponseDto>(path, accessToken, { method: "GET" });
}

export async function getAdminStats(accessToken: string | null): Promise<AdminPlatformStatsDto> {
  return apiFetchWithAuth<AdminPlatformStatsDto>("/api/v1/admin/stats", accessToken, { method: "GET" });
}

export type AdminSubscriptionOverrideDto = {
  user_id: string;
  plan_slug: string;
  status: string;
  updated_at: string;
};

// ── Audit Log ────────────────────────────────────────────────────────────

export type AdminAuditLogItemDto = {
  id: string;
  actor_user_id: string;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before_snapshot: Record<string, unknown> | null;
  after_snapshot: Record<string, unknown> | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
};

export type AdminAuditLogListResponseDto = {
  items: AdminAuditLogItemDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminAuditLogMetaDto = {
  actions: string[];
  entity_types: string[];
};

export type ListAuditLogsParams = {
  limit?: number;
  offset?: number;
  actor_user_id?: string;
  entity_type?: string;
  entity_id?: string;
  action?: string;
  since?: string;
  until?: string;
};

export async function listAdminAuditLogs(
  accessToken: string | null,
  params: ListAuditLogsParams = {},
): Promise<AdminAuditLogListResponseDto> {
  const path = withQuery("/api/v1/admin/audit-logs", {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    actor_user_id: params.actor_user_id,
    entity_type: params.entity_type,
    entity_id: params.entity_id,
    action: params.action,
    since: params.since,
    until: params.until,
  });
  return apiFetchWithAuth<AdminAuditLogListResponseDto>(path, accessToken, { method: "GET" });
}

export async function getAdminAuditLogMeta(
  accessToken: string | null,
): Promise<AdminAuditLogMetaDto> {
  return apiFetchWithAuth<AdminAuditLogMetaDto>(
    "/api/v1/admin/audit-logs/meta",
    accessToken,
    { method: "GET" },
  );
}

// ── AI Usage Monitor ─────────────────────────────────────────────────────

export type AdminAIUsagePlatformStatsDto = {
  period_days: number;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_tokens: number;
  total_cost_usd: number;
  success_rate: number;
};

export type AdminAIUsageDailyRowDto = {
  usage_date: string;
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
};

export type AdminAIUsageTopConsumerDto = {
  owner_id: string;
  owner_email: string;
  total_tokens: number;
  total_cost_usd: number;
  total_calls: number;
};

export type AdminAIUsageResponseDto = {
  stats: AdminAIUsagePlatformStatsDto;
  daily: AdminAIUsageDailyRowDto[];
  top_consumers: AdminAIUsageTopConsumerDto[];
};

export async function getAdminAIUsage(
  accessToken: string | null,
  params: { days?: number; top?: number } = {},
): Promise<AdminAIUsageResponseDto> {
  const path = withQuery("/api/v1/admin/ai-usage", {
    days: params.days ?? 30,
    top: params.top ?? 10,
  });
  return apiFetchWithAuth<AdminAIUsageResponseDto>(path, accessToken, { method: "GET" });
}

// ── Feature Flags ────────────────────────────────────────────────────────

export type FeatureFlagDto = {
  id: string;
  key: string;
  is_enabled: boolean;
  target_plan: string | null;
  target_user_ids: string[] | null;
  target_user_emails: string[] | null;
  description: string | null;
  updated_by_id: string | null;
  created_at: string;
  updated_at: string;
};

export type FeatureFlagListResponseDto = {
  items: FeatureFlagDto[];
  total: number;
};

export type FeatureFlagCreateDto = {
  key: string;
  description?: string | null;
  is_enabled?: boolean;
  target_plan?: string | null;
  target_user_emails?: string[] | null;
};

export type FeatureFlagUpdateDto = {
  is_enabled?: boolean | null;
  description?: string | null;
  target_plan?: string | null;
  clear_target_plan?: boolean;
  target_user_emails?: string[] | null;
  clear_target_users?: boolean;
};

export async function listFeatureFlags(
  accessToken: string | null,
): Promise<FeatureFlagListResponseDto> {
  return apiFetchWithAuth<FeatureFlagListResponseDto>(
    "/api/v1/admin/feature-flags",
    accessToken,
    { method: "GET" },
  );
}

export async function createFeatureFlag(
  accessToken: string | null,
  body: FeatureFlagCreateDto,
): Promise<FeatureFlagDto> {
  return apiFetchWithAuth<FeatureFlagDto>(
    "/api/v1/admin/feature-flags",
    accessToken,
    { method: "POST", body },
  );
}

export async function updateFeatureFlag(
  accessToken: string | null,
  flagId: string,
  body: FeatureFlagUpdateDto,
): Promise<FeatureFlagDto> {
  return apiFetchWithAuth<FeatureFlagDto>(
    `/api/v1/admin/feature-flags/${flagId}`,
    accessToken,
    { method: "PATCH", body },
  );
}

export async function deleteFeatureFlag(
  accessToken: string | null,
  flagId: string,
): Promise<void> {
  await apiFetchWithAuth<void>(
    `/api/v1/admin/feature-flags/${flagId}`,
    accessToken,
    { method: "DELETE" },
  );
}

// ── Support Tickets ──────────────────────────────────────────────────────

export type SupportTicketDto = {
  id: string;
  user_id: string;
  subject: string;
  body: string;
  status: string;
  priority: string;
  admin_note: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminTicketDto = SupportTicketDto & { user_email: string };

export type TicketListResponseDto = {
  items: SupportTicketDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminTicketListResponseDto = {
  items: AdminTicketDto[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminTicketUpdateDto = {
  status?: string | null;
  admin_note?: string | null;
  priority?: string | null;
};

export async function adminListTickets(
  accessToken: string | null,
  params: { status?: string; priority?: string; limit?: number; offset?: number } = {},
): Promise<AdminTicketListResponseDto> {
  const path = withQuery("/api/v1/admin/support/tickets", {
    status: params.status,
    priority: params.priority,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  });
  return apiFetchWithAuth<AdminTicketListResponseDto>(path, accessToken, { method: "GET" });
}

export async function adminUpdateTicket(
  accessToken: string | null,
  ticketId: string,
  body: AdminTicketUpdateDto,
): Promise<AdminTicketDto> {
  return apiFetchWithAuth<AdminTicketDto>(
    `/api/v1/admin/support/tickets/${ticketId}`,
    accessToken,
    { method: "PATCH", body },
  );
}

// User-facing support tickets
export async function createSupportTicket(
  accessToken: string | null,
  body: { subject: string; body: string; priority?: string },
): Promise<SupportTicketDto> {
  return apiFetchWithAuth<SupportTicketDto>("/api/v1/support/tickets", accessToken, {
    method: "POST",
    body,
  });
}

export async function listMyTickets(
  accessToken: string | null,
  params: { limit?: number; offset?: number } = {},
): Promise<TicketListResponseDto> {
  const path = withQuery("/api/v1/support/tickets", {
    limit: params.limit ?? 20,
    offset: params.offset ?? 0,
  });
  return apiFetchWithAuth<TicketListResponseDto>(path, accessToken, { method: "GET" });
}

// ── Coupons ──────────────────────────────────────────────────────────────

export type CouponDto = {
  id: string;
  code: string;
  discount_type: string;
  discount_value: string;
  target_plan: string | null;
  max_uses: number | null;
  used_count: number;
  is_active: boolean;
  expires_at: string | null;
  created_by_id: string | null;
  created_at: string;
  updated_at: string;
};

export type CouponListResponseDto = {
  items: CouponDto[];
  total: number;
};

export type CouponCreateDto = {
  code: string;
  discount_type: string;
  discount_value: string;
  target_plan?: string | null;
  max_uses?: number | null;
  expires_at?: string | null;
};

export type CouponUpdateDto = {
  is_active?: boolean | null;
  max_uses?: number | null;
  expires_at?: string | null;
  clear_expires?: boolean;
};

export async function listCoupons(accessToken: string | null): Promise<CouponListResponseDto> {
  return apiFetchWithAuth<CouponListResponseDto>("/api/v1/admin/coupons", accessToken, { method: "GET" });
}

export async function createCoupon(accessToken: string | null, body: CouponCreateDto): Promise<CouponDto> {
  return apiFetchWithAuth<CouponDto>("/api/v1/admin/coupons", accessToken, { method: "POST", body });
}

export async function updateCoupon(
  accessToken: string | null,
  couponId: string,
  body: CouponUpdateDto,
): Promise<CouponDto> {
  return apiFetchWithAuth<CouponDto>(`/api/v1/admin/coupons/${couponId}`, accessToken, { method: "PATCH", body });
}

export async function deleteCoupon(accessToken: string | null, couponId: string): Promise<void> {
  await apiFetchWithAuth<void>(`/api/v1/admin/coupons/${couponId}`, accessToken, { method: "DELETE" });
}

// ── Bulk Actions ─────────────────────────────────────────────────────────

export type BulkActionResultDto = {
  user_id: string;
  success: boolean;
  error: string | null;
};

export type BulkActionResponseDto = {
  results: BulkActionResultDto[];
  succeeded: number;
  failed: number;
};

export async function bulkUserAction(
  accessToken: string | null,
  body: { action: string; user_ids: string[]; reason?: string | null; plan_slug?: string | null },
): Promise<BulkActionResponseDto> {
  return apiFetchWithAuth<BulkActionResponseDto>("/api/v1/admin/users/bulk-action", accessToken, {
    method: "POST",
    body,
  });
}

// ── Bulk Bot Actions ────────────────────────────────────────────────────

export type BulkBotActionResultDto = {
  bot_id: string;
  success: boolean;
  error: string | null;
};

export type BulkBotActionResponseDto = {
  results: BulkBotActionResultDto[];
  succeeded: number;
  failed: number;
};

export async function bulkBotAction(
  accessToken: string | null,
  body: { action: string; bot_ids: string[]; reason?: string | null },
): Promise<BulkBotActionResponseDto> {
  return apiFetchWithAuth<BulkBotActionResponseDto>("/api/v1/admin/bots/bulk-action", accessToken, {
    method: "POST",
    body,
  });
}

// ── Impersonation ────────────────────────────────────────────────────────

export type ImpersonationResponseDto = {
  access_token: string;
  token_type: string;
  expires_in: number;
  target_user_id: string;
  target_email: string;
};

export async function impersonateUser(
  accessToken: string | null,
  userId: string,
): Promise<ImpersonationResponseDto> {
  return apiFetchWithAuth<ImpersonationResponseDto>(
    `/api/v1/admin/users/${userId}/impersonate`,
    accessToken,
    { method: "POST", body: {} },
  );
}

// ─────────────────────────────────────────────────────────────────────────

export async function adminOverrideSubscription(
  accessToken: string | null,
  userId: string,
  planSlug: string,
  reason?: string,
): Promise<AdminSubscriptionOverrideDto> {
  return apiFetchWithAuth<AdminSubscriptionOverrideDto>(
    `/api/v1/admin/users/${userId}/subscription/override`,
    accessToken,
    {
      method: "POST",
      body: { plan_slug: planSlug, reason: reason ?? null },
    },
  );
}

// ── Email Campaigns ──────────────────────────────────────────────────────

export type CampaignDto = {
  id: string;
  subject: string;
  body_html: string;
  target_segment: string;
  status: string;
  estimated_recipients: number | null;
  sent_count: number;
  failed_count: number;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CampaignListResponseDto = {
  items: CampaignDto[];
  total: number;
  limit: number;
  offset: number;
};

export type CampaignCreateDto = {
  subject: string;
  body_html: string;
  target_segment: string;
};

export type CampaignUpdateDto = {
  subject?: string | null;
  body_html?: string | null;
  target_segment?: string | null;
};

export async function listCampaigns(
  accessToken: string | null,
  params: { limit?: number; offset?: number } = {},
): Promise<CampaignListResponseDto> {
  const path = withQuery("/api/v1/admin/campaigns", {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  });
  return apiFetchWithAuth<CampaignListResponseDto>(path, accessToken, { method: "GET" });
}

export async function createCampaign(
  accessToken: string | null,
  body: CampaignCreateDto,
): Promise<CampaignDto> {
  return apiFetchWithAuth<CampaignDto>("/api/v1/admin/campaigns", accessToken, { method: "POST", body });
}

export async function updateCampaign(
  accessToken: string | null,
  campaignId: string,
  body: CampaignUpdateDto,
): Promise<CampaignDto> {
  return apiFetchWithAuth<CampaignDto>(
    `/api/v1/admin/campaigns/${campaignId}`,
    accessToken,
    { method: "PATCH", body },
  );
}

export async function sendCampaign(
  accessToken: string | null,
  campaignId: string,
): Promise<CampaignDto> {
  return apiFetchWithAuth<CampaignDto>(
    `/api/v1/admin/campaigns/${campaignId}/send`,
    accessToken,
    { method: "POST", body: {} },
  );
}

export async function deleteCampaign(
  accessToken: string | null,
  campaignId: string,
): Promise<void> {
  await apiFetchWithAuth<void>(
    `/api/v1/admin/campaigns/${campaignId}`,
    accessToken,
    { method: "DELETE" },
  );
}

// ── Segment Analytics ────────────────────────────────────────────────────

export type SegmentAnalyticsDto = {
  channels: { channel: string; count: number }[];
  niches: { niche_id: string; bot_count: number }[];
  goal_types: { goal_type: string; count: number }[];
  churn_by_plan: { plan_slug: string; canceled_count: number }[];
  signup_trend: { day: string; count: number }[];
  plan_segments: { plan_slug: string; status: string; count: number }[];
  period_days: number;
};

export async function getSegmentAnalytics(
  accessToken: string | null,
  days = 30,
): Promise<SegmentAnalyticsDto> {
  return apiFetchWithAuth<SegmentAnalyticsDto>(
    withQuery("/api/v1/admin/analytics/segments", { days }),
    accessToken,
    { method: "GET" },
  );
}

// ── Abuse Detection ──────────────────────────────────────────────────────

export type AbuseUserDto = {
  owner_id: string;
  owner_email: string;
  total_calls: number;
  failed_calls: number;
  total_tokens: number;
  total_cost_usd: string;
  error_rate: number;
};

export type ErrorCodeDto = {
  owner_id: string;
  owner_email: string;
  error_code: string;
  occurrences: number;
};

export type AbuseReportDto = {
  high_usage: AbuseUserDto[];
  top_errors: ErrorCodeDto[];
  threshold_calls: number;
  period_days: number;
};

export async function getAbuseReport(
  accessToken: string | null,
  params: { threshold_calls?: number; days?: number; limit?: number } = {},
): Promise<AbuseReportDto> {
  const path = withQuery("/api/v1/admin/abuse/report", {
    threshold_calls: params.threshold_calls ?? 500,
    days: params.days ?? 1,
    limit: params.limit ?? 50,
  });
  return apiFetchWithAuth<AbuseReportDto>(path, accessToken, { method: "GET" });
}

// ── Webhook Logs ─────────────────────────────────────────────────────────

export type WebhookLogDto = {
  id: string;
  source: string;
  event_type: string | null;
  status: string;
  error_message: string | null;
  payload_preview: Record<string, unknown> | null;
  bot_id: string | null;
  created_at: string;
  processed_at: string | null;
};

export type WebhookLogListResponseDto = {
  items: WebhookLogDto[];
  total: number;
  failed_total: number;
  limit: number;
  offset: number;
};

export async function retryWebhook(
  accessToken: string | null,
  logId: string,
): Promise<WebhookLogDto> {
  return apiFetchWithAuth<WebhookLogDto>(
    `/api/v1/admin/webhook-logs/${logId}/retry`,
    accessToken,
    { method: "POST" },
  );
}

export async function listWebhookLogs(
  accessToken: string | null,
  params: {
    source?: string;
    status?: string;
    event_type?: string;
    since?: string;
    until?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<WebhookLogListResponseDto> {
  const path = withQuery("/api/v1/admin/webhook-logs", {
    source: params.source,
    status: params.status,
    event_type: params.event_type,
    since: params.since,
    until: params.until,
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
  });
  return apiFetchWithAuth<WebhookLogListResponseDto>(path, accessToken, { method: "GET" });
}
