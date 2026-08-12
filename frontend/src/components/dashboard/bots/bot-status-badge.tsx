"use client";

import { useLanguage } from "@/contexts/language-context";
import type { WorkspaceBot } from "@/lib/api/bots";

import styles from "./bots-dashboard.module.css";

type Props = {
  status: WorkspaceBot["status"];
};

const LABEL_KEYS: Record<WorkspaceBot["status"], string> = {
  draft: "dashboard.bots.statusDraft",
  active: "dashboard.bots.statusActive",
  channel_pending: "dashboard.bots.statusChannelPending",
  paused: "dashboard.bots.statusPaused",
  archived: "dashboard.bots.statusArchived",
};

function statusClass(status: WorkspaceBot["status"]): string {
  switch (status) {
    case "draft":
      return styles.status_draft ?? "";
    case "active":
      return styles.status_active ?? "";
    case "channel_pending":
      return styles.status_channel_pending ?? "";
    case "paused":
      return styles.status_paused ?? "";
    case "archived":
      return styles.status_archived ?? "";
  }
}

export function BotStatusBadge({ status }: Props) {
  const { t } = useLanguage();

  return (
    <span className={`${styles.statusBadge} ${statusClass(status)}`} data-testid={`bot-status-${status}`}>
      {t(LABEL_KEYS[status]) as string}
    </span>
  );
}
