"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import {
  type AdminAIUsageResponseDto,
  getAdminAIUsage,
} from "@/lib/api/platform-admin";

import styles from "@/components/superadmin/superadmin.module.css";

const DAY_OPTIONS = [
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtCost(usd: number): string {
  return `$${usd.toFixed(usd < 0.01 ? 6 : 4)}`;
}

export function SuperadminAIUsage() {
  const { accessToken } = useAuth();
  const { t } = useLanguage();

  const sa = useCallback((key: string) => String(t(`superadmin.aiUsage.${key}`)), [t]);
  const sc = useCallback((key: string) => String(t(`superadmin.common.${key}`)), [t]);

  const [data, setData]       = useState<AdminAIUsageResponseDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [days, setDays]       = useState(30);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAdminAIUsage(accessToken, { days, top: 10 });
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setLoading(false);
    }
  }, [accessToken, days, sc]);

  useEffect(() => { void load(); }, [load]);

  const s = data?.stats;

  return (
    <div className={styles.stack}>
      {/* Period picker */}
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <span style={{ fontSize: "0.85rem", color: "var(--bf-text-muted)" }}>{sa("periodLabel")}</span>
        {DAY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={styles.pageBtn}
            onClick={() => setDays(opt.value)}
            style={days === opt.value ? { background: "var(--bf-accent)", color: "#fff", border: "none" } : {}}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {error && <p className={styles.errorBanner}>{error}</p>}
      {loading && <p style={{ color: "var(--bf-text-muted)" }}>{sc("loading")}</p>}

      {!loading && s && (
        <>
          {/* KPI cards */}
          <h3 style={{ margin: "0 0 0.4rem", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
            {s.period_days}d — {sa("summaryTitle")}
          </h3>
          <div className={styles.cardGrid}>
            <StatCard label={sa("totalCalls")} value={s.total_calls.toLocaleString()} />
            <StatCard label={sa("successful")} value={s.successful_calls.toLocaleString()} accent="#10b981" />
            <StatCard
              label={sa("failed")}
              value={s.failed_calls.toLocaleString()}
              accent={s.failed_calls > 0 ? "#dc2626" : undefined}
            />
            <StatCard label={sa("successRate")} value={`${(s.success_rate * 100).toFixed(1)}%`} accent="#3b82f6" />
            <StatCard label={sa("totalTokens")} value={fmtTokens(s.total_tokens)} />
            <StatCard label={sa("totalCost")} value={fmtCost(s.total_cost_usd)} accent="#f59e0b" />
          </div>

          {/* Daily usage table */}
          {data!.daily.length > 0 && (
            <>
              <h3 style={{ margin: "0.5rem 0 0.4rem", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                {sa("dailyHistory")}
              </h3>
              <div style={{ overflowX: "auto" }}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>{sa("date")}</th>
                      <th className={styles.th}>{sa("calls")}</th>
                      <th className={styles.th}>{sa("tokens")}</th>
                      <th className={styles.th}>{sa("costUsd")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data!.daily].reverse().map((row) => (
                      <tr key={row.usage_date} className={styles.row}>
                        <td className={styles.td} style={{ fontWeight: 600, fontSize: "0.82rem" }}>{row.usage_date}</td>
                        <td className={styles.td} style={{ fontSize: "0.82rem" }}>{row.total_requests.toLocaleString()}</td>
                        <td className={styles.td} style={{ fontSize: "0.82rem" }}>{fmtTokens(row.total_tokens)}</td>
                        <td className={styles.td} style={{ fontSize: "0.82rem" }}>{fmtCost(row.total_cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* Top consumers */}
          {data!.top_consumers.length > 0 && (
            <>
              <h3 style={{ margin: "0.5rem 0 0.4rem", fontSize: "0.78rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                {sa("topConsumers")}
              </h3>
              <div style={{ overflowX: "auto" }}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.th}>#</th>
                      <th className={styles.th}>{sa("user")}</th>
                      <th className={styles.th}>{sa("tokens")}</th>
                      <th className={styles.th}>{sa("calls")}</th>
                      <th className={styles.th}>{sa("cost")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data!.top_consumers.map((c, i) => (
                      <tr key={c.owner_id} className={styles.row}>
                        <td className={styles.td} style={{ fontSize: "0.82rem", color: "var(--bf-text-muted)" }}>
                          {i + 1}
                        </td>
                        <td className={styles.td} style={{ fontSize: "0.82rem" }}>
                          <Link
                            href={`/superadmin/users/${c.owner_id}`}
                            style={{ color: "var(--bf-accent)", fontWeight: 600 }}
                          >
                            {c.owner_email}
                          </Link>
                        </td>
                        <td className={styles.td} style={{ fontWeight: 700, fontSize: "0.85rem" }}>
                          {fmtTokens(c.total_tokens)}
                        </td>
                        <td className={styles.td} style={{ fontSize: "0.82rem" }}>
                          {c.total_calls.toLocaleString()}
                        </td>
                        <td className={styles.td} style={{ fontSize: "0.82rem", color: "#f59e0b", fontWeight: 600 }}>
                          {fmtCost(c.total_cost_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {data!.daily.length === 0 && data!.top_consumers.length === 0 && (
            <p style={{ color: "var(--bf-text-muted)", fontSize: "0.9rem" }}>
              {sa("noData")}
            </p>
          )}
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className={styles.statCard}>
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue} style={accent ? { color: accent } : undefined}>
        {value}
      </p>
    </div>
  );
}
