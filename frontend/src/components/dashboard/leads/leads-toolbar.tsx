"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./leads-dashboard.module.css";

export type LeadsToolbarProps = {
  status: string;
  niche: string;
  temperature: string;
  onStatusChange: (value: string) => void;
  onNicheChange: (value: string) => void;
  onTemperatureChange: (value: string) => void;
};

export function LeadsToolbar({
  status,
  niche,
  temperature,
  onStatusChange,
  onNicheChange,
  onTemperatureChange,
}: LeadsToolbarProps) {
  const { t } = useLanguage();

  const statusOptions = [
    { value: "", labelKey: "dashboard.leads.allStages" },
    { value: "new", labelKey: "dashboard.leads.stNew" },
    { value: "contacted", labelKey: "dashboard.leads.stContacted" },
    { value: "qualified", labelKey: "dashboard.leads.stQualified" },
    { value: "proposal", labelKey: "dashboard.leads.stProposal" },
    { value: "won", labelKey: "dashboard.leads.stWon" },
    { value: "lost", labelKey: "dashboard.leads.stLost" },
  ];

  const tempOptions = [
    { value: "", labelKey: "dashboard.leads.anyTemp" },
    { value: "cold", labelKey: "dashboard.leads.tempCold" },
    { value: "warm", labelKey: "dashboard.leads.tempWarm" },
    { value: "hot", labelKey: "dashboard.leads.tempHot" },
  ];

  return (
    <section className={styles.toolbar} aria-label="Lead filters" data-testid="leads-toolbar">
      <div className={styles.toolbarRow}>
        <div>
          <label className={styles.toolbarLabel} htmlFor="leads-filter-status">
            {t("dashboard.leads.pipelineStatus") as string}
          </label>
          <select
            id="leads-filter-status"
            className={styles.toolbarSelect}
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
          >
            {statusOptions.map((o) => (
              <option key={o.value || "all"} value={o.value}>
                {t(o.labelKey) as string}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={styles.toolbarLabel} htmlFor="leads-filter-temperature">
            {t("dashboard.leads.temperature") as string}
          </label>
          <select
            id="leads-filter-temperature"
            className={styles.toolbarSelect}
            value={temperature}
            onChange={(e) => onTemperatureChange(e.target.value)}
          >
            {tempOptions.map((o) => (
              <option key={o.value || "all-temp"} value={o.value}>
                {t(o.labelKey) as string}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={styles.toolbarLabel} htmlFor="leads-filter-niche">
            {t("dashboard.leads.nicheId") as string}
          </label>
          <input
            id="leads-filter-niche"
            className={styles.toolbarInput}
            type="text"
            value={niche}
            onChange={(e) => onNicheChange(e.target.value)}
            placeholder={t("dashboard.leads.nichePlaceholder") as string}
            autoComplete="off"
            maxLength={120}
          />
        </div>
      </div>
      <p className={styles.toolbarHint}>
        {t("dashboard.leads.toolbarHint") as string}
      </p>
    </section>
  );
}
