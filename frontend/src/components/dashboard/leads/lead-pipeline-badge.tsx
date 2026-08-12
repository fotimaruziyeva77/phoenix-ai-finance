"use client";

import { useLanguage } from "@/contexts/language-context";
import type { LeadPipelineStatus } from "@/lib/api/leads";

import styles from "./leads-dashboard.module.css";

const LABEL_KEYS: Record<LeadPipelineStatus, string> = {
  new: "dashboard.leads.stNew",
  contacted: "dashboard.leads.stContacted",
  qualified: "dashboard.leads.stQualified",
  proposal: "dashboard.leads.stProposal",
  won: "dashboard.leads.stWon",
  lost: "dashboard.leads.stLost",
};

type Props = {
  status: LeadPipelineStatus;
};

export function LeadPipelineBadge({ status }: Props) {
  const { t } = useLanguage();

  const cls = {
    new: styles.st_new,
    contacted: styles.st_contacted,
    qualified: styles.st_qualified,
    proposal: styles.st_proposal,
    won: styles.st_won,
    lost: styles.st_lost,
  }[status];

  return (
    <span className={`${styles.badge} ${cls}`} data-testid="lead-pipeline-badge">
      {t(LABEL_KEYS[status]) as string}
    </span>
  );
}
