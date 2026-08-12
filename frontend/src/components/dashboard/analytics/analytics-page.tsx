"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import { fetchAnalyticsSummary, type AnalyticsSummary } from "@/lib/api/analytics";

import { DonutChart } from "./mini-charts";
import styles from "./analytics-page.module.css";

// ─── color maps ───────────────────────────────────────────────────────────────

const PIPELINE_COLORS: Record<string, string> = {
  new: "#60a5fa",
  contacted: "#a78bfa",
  qualified: "#f59e0b",
  proposal: "#fb923c",
  won: "#22c55e",
  lost: "#94a3b8",
};

const TEMP_COLORS: Record<string, string> = {
  hot: "#ef4444",
  warm: "#f59e0b",
  cold: "#60a5fa",
  unknown: "#94a3b8",
};

const BOT_STATUS_COLORS: Record<string, string> = {
  active: "#22c55e",
  draft: "#94a3b8",
  paused: "#f59e0b",
  archived: "#64748b",
};

// ─── SVG icons for stat cards ───────────────────────────────────────────────

function IconBots() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={styles.statIcon} aria-hidden>
      <rect x="5" y="8" width="6" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <rect x="13" y="5" width="6" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function IconLeads() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={styles.statIcon} aria-hidden>
      <path
        d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M12.5 7a4 4 0 1 0-4 4 4 4 0 0 0 4-4Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconFire() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={styles.statIcon} aria-hidden>
      <path
        d="M12 22c4.97 0 8-3.03 8-8 0-4-4-9-8-12C8 5 4 10 4 14c0 4.97 3.03 8 8 8Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 22c2.21 0 4-2.01 4-4.5 0-2-2-4.5-4-6.5-2 2-4 4.5-4 6.5C8 19.99 9.79 22 12 22Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconTrophy() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={styles.statIcon} aria-hidden>
      <path
        d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 19.24 7 20v2h10v-2c0-.76-.85-1.25-2.03-1.79A1.13 1.13 0 0 1 14 17v-2.34"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M18 2H6v7a6 6 0 0 0 12 0V2Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── sub-components ──────────────────────────────────────────────────────────

type TFn = ReturnType<typeof useLanguage>["t"];

function StatCard({
  label,
  value,
  sub,
  Icon,
  color,
}: {
  label: string;
  value: number | string;
  sub?: string;
  Icon: () => React.ReactElement;
  color: string;
}) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statIconWrap} style={{ background: `${color}14`, color }}>
        <Icon />
      </div>
      <div className={styles.statContent}>
        <span className={styles.statLabel}>{label}</span>
        <span className={styles.statValue}>{value}</span>
        {sub && <span className={styles.statSub}>{sub}</span>}
      </div>
    </div>
  );
}

function PipelinePanel({
  leads,
  t,
}: {
  leads: AnalyticsSummary["leads"];
  t: TFn;
}) {
  const keys = ["new", "contacted", "qualified", "proposal", "won", "lost"] as const;
  const labelKeys: Record<string, string> = {
    new: "dashboard.analytics.stNew",
    contacted: "dashboard.analytics.stContacted",
    qualified: "dashboard.analytics.stQualified",
    proposal: "dashboard.analytics.stProposal",
    won: "dashboard.analytics.stWon",
    lost: "dashboard.analytics.stLost",
  };

  const max = Math.max(1, ...keys.map((k) => leads[k]));

  const donutSegments = keys.map((k) => ({
    label: t(labelKeys[k]!) as string,
    value: leads[k],
    color: PIPELINE_COLORS[k] ?? "#94a3b8",
  }));

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>{t("dashboard.analytics.leadPipeline") as string}</p>
      {leads.total === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M22 12h-6l-2 3H10l-2-3H2"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className={styles.emptyText}>{t("dashboard.analytics.noLeadsYet") as string}</p>
        </div>
      ) : (
        <>
          <div className={styles.panelChartSection}>
            <DonutChart
              segments={donutSegments}
              centerLabel={String(leads.total)}
              centerSub={t("dashboard.analytics.total") as string}
              ariaLabel={`${t("dashboard.analytics.leadPipeline") as string}: ${leads.total}`}
            />
          </div>

          <div className={styles.pipelineList}>
            {keys.map((status) => {
              const count = leads[status];
              const pct = Math.round((count / max) * 100);
              return (
                <div key={status} className={styles.pipelineRow}>
                  <div className={styles.pipelineMeta}>
                    <span className={styles.pipelineDot} style={{ background: PIPELINE_COLORS[status] }} />
                    <span className={styles.pipelineLabel}>{t(labelKeys[status]!) as string}</span>
                    <span className={styles.pipelineCount}>{count}</span>
                  </div>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{
                        width: `${Math.max(pct, count > 0 ? 6 : 0)}%`,
                        background: PIPELINE_COLORS[status] ?? "#94a3b8",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function TemperaturePanel({
  temp,
  t,
}: {
  temp: AnalyticsSummary["lead_temperature"];
  t: TFn;
}) {
  const rows: { key: keyof typeof temp; labelKey: string }[] = [
    { key: "hot", labelKey: "dashboard.analytics.tempHot" },
    { key: "warm", labelKey: "dashboard.analytics.tempWarm" },
    { key: "cold", labelKey: "dashboard.analytics.tempCold" },
    { key: "unknown", labelKey: "dashboard.analytics.tempUnknown" },
  ];
  const total = Object.values(temp).reduce((s, v) => s + v, 0);

  const donutSegments = rows.map(({ key, labelKey }) => ({
    label: t(labelKey) as string,
    value: temp[key],
    color: TEMP_COLORS[key] ?? "#94a3b8",
  }));

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>{t("dashboard.analytics.leadTemperature") as string}</p>
      {total === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0Z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className={styles.emptyText}>{t("dashboard.analytics.noLeadsYet") as string}</p>
        </div>
      ) : (
        <DonutChart
          segments={donutSegments}
          centerLabel={String(total)}
          centerSub={t("dashboard.analytics.leads") as string}
          ariaLabel={`${t("dashboard.analytics.leadTemperature") as string}: ${total}`}
        />
      )}
    </div>
  );
}

function BotStatusPanel({
  bots,
  t,
}: {
  bots: AnalyticsSummary["bots"];
  t: TFn;
}) {
  const rows: { key: keyof Omit<typeof bots, "total">; labelKey: string }[] = [
    { key: "active", labelKey: "dashboard.analytics.botActive" },
    { key: "draft", labelKey: "dashboard.analytics.botDraft" },
    { key: "paused", labelKey: "dashboard.analytics.botPaused" },
    { key: "archived", labelKey: "dashboard.analytics.botArchived" },
  ];

  const max = Math.max(1, ...rows.map(({ key }) => bots[key]));

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>{t("dashboard.analytics.botStatus") as string}</p>
      {bots.total === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden>
              <rect x="5" y="8" width="6" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <rect x="13" y="5" width="6" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </div>
          <p className={styles.emptyText}>
            {t("dashboard.analytics.noBotsYet") as string}
            {" — "}
            <Link href="/dashboard/bots" className={styles.emptyLink}>
              {t("dashboard.analytics.createOne") as string}
            </Link>
          </p>
        </div>
      ) : (
        <div className={styles.pipelineList}>
          {rows.map(({ key, labelKey }) => {
            const count = bots[key];
            const pct = Math.round((count / max) * 100);
            return (
              <div key={key} className={styles.pipelineRow}>
                <div className={styles.pipelineMeta}>
                  <span className={styles.pipelineDot} style={{ background: BOT_STATUS_COLORS[key] }} />
                  <span className={styles.pipelineLabel}>{t(labelKey) as string}</span>
                  <span className={styles.pipelineCount}>{count}</span>
                </div>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{
                      width: `${Math.max(pct, count > 0 ? 6 : 0)}%`,
                      background: BOT_STATUS_COLORS[key] ?? "#94a3b8",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function UsagePanel({
  usage,
  t,
}: {
  usage: AnalyticsSummary["usage"];
  t: TFn;
}) {
  const limitLabel =
    usage.conversations_limit === null
      ? (t("dashboard.analytics.unlimited") as string)
      : usage.conversations_limit.toLocaleString();

  const usedPct =
    usage.conversations_limit !== null && usage.conversations_limit > 0
      ? Math.min(100, Math.round((usage.conversations_this_month / usage.conversations_limit) * 100))
      : 0;

  return (
    <div className={styles.panel}>
      <div className={styles.panelTitleRow}>
        <p className={styles.panelTitle}>{t("dashboard.analytics.planUsage") as string}</p>
        <span className={styles.planBadge}>{usage.plan_name}</span>
      </div>
      <div className={styles.usageGrid}>
        <div className={styles.usageItem}>
          <span className={styles.usageLabel}>{t("dashboard.analytics.plan") as string}</span>
          <span className={styles.usageValue}>{usage.plan_name}</span>
        </div>
        <div className={styles.usageItem}>
          <span className={styles.usageLabel}>{t("dashboard.analytics.conversationsMonth") as string}</span>
          <span className={styles.usageValue}>{usage.conversations_this_month.toLocaleString()}</span>
          <span className={styles.usageSub}>
            {t("dashboard.analytics.of") as string} {limitLabel}
          </span>
          {usage.conversations_limit !== null && (
            <div className={styles.usageBar}>
              <div
                className={styles.usageBarFill}
                style={{
                  width: `${usedPct}%`,
                  background: usedPct > 80 ? "#f59e0b" : usedPct > 95 ? "#ef4444" : "#22c55e",
                }}
              />
            </div>
          )}
        </div>
      </div>
      <p className={styles.billingHint}>
        {t("dashboard.analytics.billingHint") as string}{" "}
        <Link href="/dashboard/billing" className={styles.billingLink}>
          {t("dashboard.analytics.billingLink") as string}
        </Link>
        .
      </p>
    </div>
  );
}

// ─── period toggle ────────────────────────────────────────────────────────────

const PERIOD_DAYS = [7, 30, 90] as const;

// ─── main component ───────────────────────────────────────────────────────────

export function AnalyticsPage() {
  const { t } = useLanguage();
  const { accessToken } = useAuth();
  const [periodDays, setPeriodDays] = useState(30);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const periodSuffix = t("dashboard.analytics.periodDays") as string;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    async function load() {
      try {
        const data = await fetchAnalyticsSummary(accessToken, periodDays);
        if (!alive) return;
        setSummary(data);
      } catch (e: unknown) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : (t("dashboard.analytics.loadError") as string));
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, [accessToken, periodDays, t]);

  if (loading) {
    return (
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>{t("dashboard.analytics.loading") as string}</p>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className={styles.loadingWrap}>
        <p className={styles.loadingText}>{error ?? (t("dashboard.analytics.noData") as string)}</p>
      </div>
    );
  }

  const convRate =
    summary.leads.total > 0
      ? Math.round((summary.leads.won / summary.leads.total) * 100)
      : 0;

  return (
    <div className={styles.stack} data-testid="analytics-page-root">
      {/* ── Page header ───────────────────────────────────── */}
      <header className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>{t("dashboard.analytics.title") as string}</h1>
          <p className={styles.pageSubtitle}>{t("dashboard.analytics.subtitle") as string}</p>
        </div>
        <div className={styles.periodRow}>
          <span className={styles.periodLabel}>{t("dashboard.analytics.period") as string}:</span>
          {PERIOD_DAYS.map((days) => (
            <button
              key={days}
              className={`${styles.periodBtn} ${periodDays === days ? styles.periodBtnActive : ""}`}
              onClick={() => setPeriodDays(days)}
            >
              {days}
              {periodSuffix}
            </button>
          ))}
        </div>
      </header>

      {error && <div className={styles.errorBanner}>{error}</div>}

      {/* ── Stat cards ──────────────────────────────────── */}
      <div className={styles.statsGrid}>
        <StatCard
          label={t("dashboard.analytics.totalBots") as string}
          value={summary.bots.total}
          sub={`${summary.bots.active} ${t("dashboard.analytics.activeCount") as string}`}
          Icon={IconBots}
          color="#60a5fa"
        />
        <StatCard
          label={t("dashboard.analytics.totalLeads") as string}
          value={summary.leads.total}
          sub={`${t("dashboard.analytics.lastDays") as string} ${periodDays}${periodSuffix}`}
          Icon={IconLeads}
          color="#a78bfa"
        />
        <StatCard
          label={t("dashboard.analytics.hotLeads") as string}
          value={summary.lead_temperature.hot}
          sub={t("dashboard.analytics.highIntent") as string}
          Icon={IconFire}
          color="#ef4444"
        />
        <StatCard
          label={t("dashboard.analytics.wonLeads") as string}
          value={summary.leads.won}
          sub={`${convRate}% ${t("dashboard.analytics.convRate") as string}`}
          Icon={IconTrophy}
          color="#22c55e"
        />
      </div>

      {/* ── Pipeline + Temperature ───────────────────────── */}
      <div className={styles.panelsRow}>
        <PipelinePanel leads={summary.leads} t={t} />
        <TemperaturePanel temp={summary.lead_temperature} t={t} />
      </div>

      {/* ── Bot status + Plan usage ──────────────────────── */}
      <div className={styles.panelsRow}>
        <BotStatusPanel bots={summary.bots} t={t} />
        <UsagePanel usage={summary.usage} t={t} />
      </div>
    </div>
  );
}
