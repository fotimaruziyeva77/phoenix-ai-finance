"use client";

import { useLanguage } from "@/contexts/language-context";
import type { WorkspaceLead } from "@/lib/api/leads";

import styles from "./leads-dashboard.module.css";

type Props = {
  leads: WorkspaceLead[];
  total: number;
};

type StatItem = {
  labelKey: string;
  value: number;
  color: string;
};

export function LeadsStatsBar({ leads, total }: Props) {
  const { t } = useLanguage();

  if (total === 0) return null;

  // Count by pipeline status
  const statusCounts = { new: 0, contacted: 0, qualified: 0, proposal: 0, won: 0, lost: 0 };
  const tempCounts = { cold: 0, warm: 0, hot: 0 };

  for (const lead of leads) {
    if (lead.status in statusCounts) statusCounts[lead.status]++;
    if (lead.temperature && lead.temperature in tempCounts) tempCounts[lead.temperature]++;
  }

  const pipelineStats: StatItem[] = [
    { labelKey: "dashboard.leads.statsNew", value: statusCounts.new, color: "#3b82f6" },
    { labelKey: "dashboard.leads.statsQualified", value: statusCounts.qualified, color: "#a855f7" },
    { labelKey: "dashboard.leads.statsWon", value: statusCounts.won, color: "#22c55e" },
    { labelKey: "dashboard.leads.statsLost", value: statusCounts.lost, color: "#64748b" },
  ];

  const tempStats: StatItem[] = [
    { labelKey: "dashboard.leads.statsHot", value: tempCounts.hot, color: "#f43f5e" },
    { labelKey: "dashboard.leads.statsWarm", value: tempCounts.warm, color: "#f59e0b" },
    { labelKey: "dashboard.leads.statsCold", value: tempCounts.cold, color: "#64748b" },
  ];

  const maxPipeline = Math.max(...pipelineStats.map((s) => s.value), 1);
  const maxTemp = Math.max(...tempStats.map((s) => s.value), 1);

  return (
    <div className={styles.statsRow}>
      {/* Total */}
      <div className={styles.statCard}>
        <span className={styles.statValue}>{total}</span>
        <span className={styles.statLabel}>{t("dashboard.leads.statsTotal") as string}</span>
      </div>

      {/* Pipeline mini-bars */}
      <div className={styles.statBarGroup}>
        <span className={styles.statBarGroupTitle}>{t("dashboard.leads.pipelineStatus") as string}</span>
        {pipelineStats.map(({ labelKey, value, color }) => (
          <div key={labelKey} className={styles.statBarRow}>
            <span className={styles.statBarLabel}>{t(labelKey) as string}</span>
            <div className={styles.statBarTrack}>
              <div
                className={styles.statBarFill}
                style={{
                  width: `${Math.max((value / maxPipeline) * 100, value > 0 ? 8 : 0)}%`,
                  backgroundColor: color,
                }}
              />
            </div>
            <span className={styles.statBarValue}>{value}</span>
          </div>
        ))}
      </div>

      {/* Temperature mini-bars */}
      <div className={styles.statBarGroup}>
        <span className={styles.statBarGroupTitle}>{t("dashboard.leads.temperature") as string}</span>
        {tempStats.map(({ labelKey, value, color }) => (
          <div key={labelKey} className={styles.statBarRow}>
            <span className={styles.statBarLabel}>{t(labelKey) as string}</span>
            <div className={styles.statBarTrack}>
              <div
                className={styles.statBarFill}
                style={{
                  width: `${Math.max((value / maxTemp) * 100, value > 0 ? 8 : 0)}%`,
                  backgroundColor: color,
                }}
              />
            </div>
            <span className={styles.statBarValue}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
