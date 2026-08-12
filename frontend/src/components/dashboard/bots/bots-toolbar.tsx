"use client";

import { useLanguage } from "@/contexts/language-context";
import type { WorkspaceBot } from "@/lib/api/bots";

import styles from "./bots-dashboard.module.css";

type Props = {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  statusFilter: WorkspaceBot["status"] | "";
  onStatusChange: (value: WorkspaceBot["status"] | "") => void;
};

export function BotsToolbar({ searchQuery, onSearchChange, statusFilter, onStatusChange }: Props) {
  const { t } = useLanguage();

  return (
    <div className={styles.toolbar} role="search" aria-label="Bot list filters">
      <div className={styles.toolbarRow}>
        <label className={styles.toolbarLabel} htmlFor="bots-search">
          {t("dashboard.bots.search") as string}
        </label>
        <input
          id="bots-search"
          className={styles.toolbarInput}
          type="search"
          placeholder={t("dashboard.bots.searchPlaceholder") as string}
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          data-testid="bots-search"
        />
        <label className={styles.toolbarLabel} htmlFor="bots-status-filter">
          {t("dashboard.bots.status") as string}
        </label>
        <select
          id="bots-status-filter"
          className={styles.toolbarSelect}
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value as WorkspaceBot["status"] | "")}
          data-testid="bots-status-filter"
        >
          <option value="">{t("dashboard.bots.allStatuses") as string}</option>
          <option value="draft">{t("dashboard.bots.statusDraft") as string}</option>
          <option value="active">{t("dashboard.bots.statusActive") as string}</option>
          <option value="channel_pending">{t("dashboard.bots.statusChannelPending") as string}</option>
          <option value="paused">{t("dashboard.bots.statusPaused") as string}</option>
          <option value="archived">{t("dashboard.bots.statusArchived") as string}</option>
        </select>
      </div>
    </div>
  );
}
