import { apiFetchWithAuth } from "./client";

export type BotStatusBreakdown = {
  draft: number;
  active: number;
  paused: number;
  archived: number;
  total: number;
};

export type LeadStatusBreakdown = {
  new: number;
  contacted: number;
  qualified: number;
  proposal: number;
  won: number;
  lost: number;
  total: number;
};

export type LeadTemperatureBreakdown = {
  hot: number;
  warm: number;
  cold: number;
  unknown: number;
};

export type UsageSummary = {
  conversations_this_month: number;
  conversations_limit: number | null;
  plan_slug: string;
  plan_name: string;
};

export type AnalyticsSummary = {
  bots: BotStatusBreakdown;
  leads: LeadStatusBreakdown;
  lead_temperature: LeadTemperatureBreakdown;
  usage: UsageSummary;
  period_days: number;
  generated_at: string;
};

export async function fetchAnalyticsSummary(
  accessToken: string | null,
  periodDays: number = 30,
): Promise<AnalyticsSummary> {
  return apiFetchWithAuth<AnalyticsSummary>(
    `/api/v1/analytics/summary?period_days=${periodDays}`,
    accessToken,
    { method: "GET" },
  );
}
