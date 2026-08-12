"use client";

import { useLanguage } from "@/contexts/language-context";
import type { LeadTemperature } from "@/lib/api/leads";

import styles from "./leads-dashboard.module.css";

const LABEL_KEYS: Record<LeadTemperature, string> = {
  cold: "dashboard.leads.tempCold",
  warm: "dashboard.leads.tempWarm",
  hot: "dashboard.leads.tempHot",
};

type Props = {
  temperature: LeadTemperature | null;
};

export function LeadTemperatureBadge({ temperature }: Props) {
  const { t } = useLanguage();

  if (!temperature) {
    return (
      <span className={`${styles.badge} ${styles.tp_none}`} data-testid="lead-temperature-badge">
        —
      </span>
    );
  }
  const cls = {
    cold: styles.tp_cold,
    warm: styles.tp_warm,
    hot: styles.tp_hot,
  }[temperature];

  return (
    <span className={`${styles.badge} ${cls}`} data-testid="lead-temperature-badge">
      {t(LABEL_KEYS[temperature]) as string}
    </span>
  );
}
