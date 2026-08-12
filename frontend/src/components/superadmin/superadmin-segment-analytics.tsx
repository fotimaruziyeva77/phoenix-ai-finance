"use client";

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import { getSegmentAnalytics, type SegmentAnalyticsDto } from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

const CHANNEL_COLORS: Record<string, string> = {
  web_widget: "#3b82f6",
  telegram: "#0ea5e9",
  admin_test: "#6b7280",
};

const PERIOD_OPTIONS = [7, 30, 90];

export function SuperadminSegmentAnalytics() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const sa = (key: string) => String(t(`superadmin.analytics.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const CHANNEL_LABELS: Record<string, string> = {
    web_widget: sa("channelWebWidget"),
    telegram: sa("channelTelegram"),
    admin_test: sa("channelAdminTest"),
  };

  const [data, setData] = useState<SegmentAnalyticsDto | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(d = days) {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await getSegmentAnalytics(token, d);
      setData(res);
    } catch {
      setError(sa("loadError"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [token, days]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalConversations = data?.channels.reduce((s, c) => s + c.count, 0) ?? 0;

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}

      <div className={styles.toolbar}>
        {PERIOD_OPTIONS.map(d => (
          <button key={d} className={days === d ? styles.btnPrimary : styles.btnNeutral} onClick={() => setDays(d)}>
            {d}d
          </button>
        ))}
        <span className={styles.toolbarMeta}>{loading ? sc("loading") : `${sa("periodLabel")} ${days}d`}</span>
      </div>

      {data && (
        <>
          {/* Channel Distribution */}
          <section>
            <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>
              {sa("channelDistribution")} ({totalConversations.toLocaleString()})
            </h3>
            <div className={styles.chartRow}>
              <div className={styles.cardGrid} style={{ alignContent: "start" }}>
                {data.channels.map(c => (
                  <div key={c.channel} className={styles.statCard}>
                    <p className={styles.statLabel}>{CHANNEL_LABELS[c.channel] ?? c.channel}</p>
                    <p className={styles.statValue}>{c.count.toLocaleString()}</p>
                    <p className={styles.cellSub}>{totalConversations > 0 ? `${((c.count / totalConversations) * 100).toFixed(1)}%` : "—"}</p>
                  </div>
                ))}
                {data.channels.length === 0 && <p className={styles.pageIntro}>{sa("noConversationData")}</p>}
              </div>

              {/* Channel Pie Chart */}
              {data.channels.length > 0 && (
                <div className={styles.chartContainer}>
                  <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                    {sa("channelChart")}
                  </h4>
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={data.channels}
                        dataKey="count"
                        nameKey="channel"
                        cx="50%"
                        cy="50%"
                        outerRadius={75}
                        label={(props) => {
                          const channel = String(props.name ?? "");
                          const pct = typeof props.percent === "number" ? (props.percent * 100).toFixed(0) : "0";
                          return `${CHANNEL_LABELS[channel] ?? channel} ${pct}%`;
                        }}
                        labelLine={{ stroke: "var(--bf-text-muted)" }}
                      >
                        {data.channels.map((entry) => (
                          <Cell
                            key={entry.channel}
                            fill={CHANNEL_COLORS[entry.channel] ?? "#6b7280"}
                          />
                        ))}
                      </Pie>
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
                      <Legend
                        formatter={(value: string) => CHANNEL_LABELS[value] ?? value}
                        wrapperStyle={{ fontSize: "0.78rem" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </section>

          {/* Signup Trend */}
          <section>
            <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>
              {sa("userSignups")} ({days}d)
            </h3>
            {data.signup_trend.length === 0 ? (
              <p className={styles.pageIntro}>{sa("noSignupData")}</p>
            ) : (
              <>
                {/* Signup Trend Chart */}
                <div className={styles.chartContainer} style={{ marginBottom: "1rem" }}>
                  <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
                    {sa("signupChart")}
                  </h4>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart
                      data={data.signup_trend}
                      margin={{ top: 4, right: 12, bottom: 4, left: 0 }}
                    >
                      <defs>
                        <linearGradient id="signupGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--bf-accent)" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="var(--bf-accent)" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--bf-border)" opacity={0.5} />
                      <XAxis
                        dataKey="day"
                        tick={{ fill: "var(--bf-text-muted)", fontSize: 11 }}
                        axisLine={{ stroke: "var(--bf-border)" }}
                        tickLine={false}
                        tickFormatter={(v: string) => v.slice(5)}
                      />
                      <YAxis
                        tick={{ fill: "var(--bf-text-muted)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        allowDecimals={false}
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
                      <Area
                        type="monotone"
                        dataKey="count"
                        stroke="var(--bf-accent)"
                        strokeWidth={2}
                        fill="url(#signupGrad)"
                        dot={{ r: 3, fill: "var(--bf-accent)", strokeWidth: 0 }}
                        activeDot={{ r: 5, fill: "var(--bf-accent)", strokeWidth: 0 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Signup Trend Detail Table */}
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th className={styles.th}>{sa("date")}</th>
                        <th className={styles.th}>{sa("newUsers")}</th>
                        <th className={styles.th}>{sa("bar")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const max = Math.max(...data.signup_trend.map(t => t.count), 1);
                        return data.signup_trend.slice().reverse().map(t => (
                          <tr key={t.day} className={styles.row}>
                            <td className={styles.td}>{t.day}</td>
                            <td className={styles.td} style={{ fontWeight: 600 }}>{t.count}</td>
                            <td className={styles.td}>
                              <div style={{ height: "8px", borderRadius: "4px", background: "color-mix(in srgb, var(--bf-accent) 25%, transparent)", width: "100%", maxWidth: "12rem" }}>
                                <div style={{ height: "100%", borderRadius: "4px", background: "var(--bf-accent)", width: `${(t.count / max) * 100}%` }} />
                              </div>
                            </td>
                          </tr>
                        ));
                      })()}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>

          {/* Plan Segments + Churn */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <section>
              <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>{sa("planSegments")}</h3>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead><tr><th className={styles.th}>{sa("plan")}</th><th className={styles.th}>{sa("status")}</th><th className={styles.th}>{sa("count")}</th></tr></thead>
                  <tbody>
                    {data.plan_segments.map((p, i) => (
                      <tr key={i} className={styles.row}>
                        <td className={styles.td}><span className={styles.badgeOk}>{p.plan_slug}</span></td>
                        <td className={styles.td}>{p.status}</td>
                        <td className={styles.td} style={{ fontWeight: 600 }}>{p.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>{sa("churnByPlan")}</h3>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead><tr><th className={styles.th}>{sa("plan")}</th><th className={styles.th}>{sa("canceled")}</th></tr></thead>
                  <tbody>
                    {data.churn_by_plan.length === 0 ? (
                      <tr><td className={styles.td} colSpan={2} style={{ color: "var(--bf-text-muted)" }}>{sa("noChurnData")}</td></tr>
                    ) : data.churn_by_plan.map((c, i) => (
                      <tr key={i} className={styles.row}>
                        <td className={styles.td}>{c.plan_slug}</td>
                        <td className={styles.td} style={{ fontWeight: 600, color: "#c0392b" }}>{c.canceled_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          {/* Niche + Goal Type */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <section>
              <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>{sa("botsByNiche")}</h3>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead><tr><th className={styles.th}>{sa("niche")}</th><th className={styles.th}>{sa("bots")}</th></tr></thead>
                  <tbody>
                    {data.niches.slice(0, 10).map((n, i) => (
                      <tr key={i} className={styles.row}>
                        <td className={styles.td}>{n.niche_id}</td>
                        <td className={styles.td} style={{ fontWeight: 600 }}>{n.bot_count}</td>
                      </tr>
                    ))}
                    {data.niches.length === 0 && <tr><td className={styles.td} colSpan={2} style={{ color: "var(--bf-text-muted)" }}>{sa("noData")}</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>{sa("botsByGoal")}</h3>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead><tr><th className={styles.th}>{sa("goal")}</th><th className={styles.th}>{sa("count")}</th></tr></thead>
                  <tbody>
                    {data.goal_types.map((g, i) => (
                      <tr key={i} className={styles.row}>
                        <td className={styles.td}>{g.goal_type}</td>
                        <td className={styles.td} style={{ fontWeight: 600 }}>{g.count}</td>
                      </tr>
                    ))}
                    {data.goal_types.length === 0 && <tr><td className={styles.td} colSpan={2} style={{ color: "var(--bf-text-muted)" }}>{sa("noData")}</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
