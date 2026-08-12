"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from "recharts";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  getAdminStats,
  listAdminAuditLogs,
  type AdminPlatformStatsDto,
  type AdminAuditLogItemDto,
} from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";

import styles from "./superadmin.module.css";

const PLAN_COLORS: Record<string, string> = {
  free: "#6b7280",
  pro: "#8b5cf6",
  business: "#f59e0b",
  enterprise: "#10b981",
};

const ACTION_DOT_COLORS: Record<string, string> = {
  user_suspended: "#dc2626",
  user_unsuspended: "#10b981",
  bot_platform_suspended: "#dc2626",
  bot_platform_unsuspended: "#10b981",
  bot_created: "#3b82f6",
  feature_flag_created: "#8b5cf6",
  feature_flag_updated: "#f59e0b",
  campaign_sent: "#3b82f6",
};

function StatCard({
  label,
  value,
  sub,
  accent,
  testId,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  testId?: string;
}) {
  return (
    <div className={styles.statCard}>
      <p className={styles.statLabel}>{label}</p>
      <p
        className={styles.statValue}
        style={accent ? { color: accent } : undefined}
        data-testid={testId}
      >
        {value}
      </p>
      {sub && <p style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)", marginTop: "0.2rem" }}>{sub}</p>}
    </div>
  );
}

export function SuperadminOverview() {
  const { t } = useLanguage();
  const so = (key: string) => String(t(`superadmin.overview.${key}`));
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<AdminPlatformStatsDto | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(60);
  const [recentActivity, setRecentActivity] = useState<AdminAuditLogItemDto[]>([]);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setLoading(true);
    setError(null);
    try {
      const [data, actRes] = await Promise.all([
        getAdminStats(accessToken),
        listAdminAuditLogs(accessToken, { limit: 8 }),
      ]);
      setStats(data);
      setRecentActivity(actRes.items);
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => { void load(); }, refreshInterval * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, load]);

  return (
    <div className={styles.stack}>
      <p className={styles.pageIntro}>
        {so("intro")}
      </p>

      {/* Auto-refresh toolbar */}
      <div className={styles.toolbar}>
        <button
          type="button"
          className={autoRefresh ? styles.btnPrimary : styles.btnNeutral}
          onClick={() => setAutoRefresh((v) => !v)}
        >
          {so("autoRefresh")}
        </button>
        {([30, 60, 120] as const).map((sec) => (
          <button
            key={sec}
            type="button"
            className={refreshInterval === sec ? styles.btnPrimary : styles.btnNeutral}
            style={{ padding: "0.35rem 0.6rem", fontSize: "0.78rem" }}
            onClick={() => setRefreshInterval(sec)}
          >
            {sec}{so("seconds")}
          </button>
        ))}
        {autoRefresh && (
          <span className={styles.toolbarMeta}>
            {so("refreshEvery")} {refreshInterval}{so("seconds")}
          </span>
        )}
      </div>

      {error ? <p className={styles.errorBanner}>{error}</p> : null}
      {loading ? <p className={styles.pageIntro}>{so("loadingOverview")}</p> : null}

      {!loading && stats ? (
        <>
          {/* Users & Bots */}
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
            {so("usersAndBots")}
          </h3>
          <div className={styles.cardGrid}>
            <StatCard label={so("registeredUsers")} value={stats.total_users} testId="superadmin-overview-total-users" />
            <StatCard label={so("activeUsers")} value={stats.active_users} testId="superadmin-overview-active-users" />
            <StatCard label={so("totalBots")} value={stats.total_bots} testId="superadmin-overview-total-bots" />
            <StatCard label={so("activeBots")} value={stats.active_bots} testId="superadmin-overview-active-bots" />
            <StatCard label={so("leads")} value={stats.total_leads} />
            <StatCard label={so("conversations")} value={stats.total_conversations} />
          </div>

          {/* Billing KPIs */}
          <h3 style={{ margin: "1.25rem 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
            {so("billingRevenue")}
          </h3>
          <div className={styles.cardGrid}>
            <StatCard
              label={so("mrr")}
              value={`$${stats.mrr_usd.toFixed(0)}`}
              sub={so("mrrSub")}
              accent="#10b981"
              testId="superadmin-overview-mrr"
            />
            <StatCard
              label={so("paidActive")}
              value={stats.total_paid_active}
              sub={so("paidActiveSub")}
              accent="#3b82f6"
            />
            <StatCard
              label={so("freePlan")}
              value={stats.total_free}
              sub={so("freePlanSub")}
            />
            <StatCard
              label={so("pastDue")}
              value={stats.total_past_due}
              sub={so("pastDueSub")}
              accent={stats.total_past_due > 0 ? "#dc2626" : undefined}
            />
            <StatCard
              label={so("canceled")}
              value={stats.total_canceled}
              sub={so("canceledSub")}
            />
          </div>

          {/* Plan distribution chart */}
          {stats.subscription_distribution.length > 0 && (
            <>
              <h3 style={{ margin: "1.25rem 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                {so("planChart")}
              </h3>
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={stats.subscription_distribution}
                    layout="vertical"
                    margin={{ top: 4, right: 32, bottom: 4, left: 8 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="plan_slug"
                      width={80}
                      tick={{ fill: "var(--bf-text-muted)", fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--bf-card)",
                        border: "1px solid var(--bf-border)",
                        borderRadius: 8,
                        fontSize: "0.8125rem",
                      }}
                      labelStyle={{ color: "var(--bf-text)", fontWeight: 600 }}
                      itemStyle={{ color: "var(--bf-text)" }}
                    />
                    <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={24} label={{ position: "right", fill: "var(--bf-text)", fontSize: 13, fontWeight: 600 }}>
                      {stats.subscription_distribution.map((entry) => (
                        <Cell
                          key={entry.plan_slug}
                          fill={PLAN_COLORS[entry.plan_slug] ?? "#6b7280"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {/* Recent Activity */}
          {recentActivity.length > 0 && (
            <>
              <h3 style={{ margin: "1.25rem 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                {so("recentActivity")}
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {recentActivity.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      display: "flex",
                      gap: "0.75rem",
                      alignItems: "flex-start",
                      padding: "0.5rem 0.75rem",
                      borderRadius: 8,
                      background: "color-mix(in srgb, var(--bf-surface) 90%, var(--bf-border))",
                      border: "1px solid color-mix(in srgb, var(--bf-border) 50%, transparent)",
                      fontSize: "0.8125rem",
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        flexShrink: 0,
                        marginTop: 6,
                        background: ACTION_DOT_COLORS[item.action] ?? "var(--bf-text-muted)",
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <span style={{ fontWeight: 600 }}>{item.action.replace(/_/g, " ")}</span>
                      {item.actor_email && (
                        <span style={{ color: "var(--bf-text-muted)", marginLeft: "0.5rem" }}>
                          by {item.actor_email}
                        </span>
                      )}
                      <div style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)", marginTop: 2 }}>
                        {item.entity_type} · {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <p style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)", marginTop: "1rem" }}>
            {so("generatedAt")} {new Date(stats.generated_at).toLocaleString()}{" "}
            &middot;{" "}
            <Link href="/superadmin/billing" style={{ color: "var(--bf-accent)" }}>{so("viewBilling")} →</Link>
          </p>
        </>
      ) : null}
    </div>
  );
}
