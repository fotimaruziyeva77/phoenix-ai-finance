"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";
import type { WorkspaceLead } from "@/lib/api/leads";
import { formatDashboardDate } from "@/lib/format/datetime";

import { LeadPipelineBadge } from "./lead-pipeline-badge";
import { LeadTemperatureBadge } from "./lead-temperature-badge";
import styles from "./leads-dashboard.module.css";

export type LeadsListProps = {
  leads: WorkspaceLead[];
  hasMore?: boolean;
  loadingMore?: boolean;
  onLoadMore?: () => void;
};

function formatPhoneDisplay(phone: string | null): string {
  if (!phone) return "—";
  return phone;
}

function formatScoreDisplay(score: number | null): string {
  if (score === null) return "—";
  return String(score);
}

/** Single lead row — table cell group (reuse via composition). */
export function LeadSummaryCell({ lead }: { lead: WorkspaceLead }) {
  return (
    <div>
      <p className={styles.leadTitle}>
        <Link href={`/dashboard/leads/${lead.id}`} className={styles.leadTitleLink}>
          {lead.displayTitle}
        </Link>
      </p>
      {lead.subtitle ? <p className={styles.leadSubtitle}>{lead.subtitle}</p> : null}
    </div>
  );
}

export function LeadsList({ leads, hasMore, loadingMore, onLoadMore }: LeadsListProps) {
  const { t } = useLanguage();

  return (
    <div className={styles.listShell} data-testid="leads-list-shell">
      <div className={styles.listTableWrap} role="region" aria-label="Leads table" data-testid="leads-list-table">
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colLead") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colStatus") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colTemp") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colScore") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colNiche") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colPhone") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.leads.colCreated") as string}
              </th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} data-testid="leads-list-row">
                <td className={styles.td}>
                  <LeadSummaryCell lead={lead} />
                </td>
                <td className={styles.td}>
                  <LeadPipelineBadge status={lead.status} />
                </td>
                <td className={styles.td}>
                  <LeadTemperatureBadge temperature={lead.temperature} />
                </td>
                <td className={`${styles.td} ${styles.tdMuted}`} data-testid="lead-score-cell">
                  {formatScoreDisplay(lead.leadScore)}
                </td>
                <td className={`${styles.td} ${styles.tdMuted}`}>{lead.nicheLabel}</td>
                <td className={`${styles.td} ${styles.phoneCell}`}>{formatPhoneDisplay(lead.phone)}</td>
                <td className={`${styles.td} ${styles.tdMuted}`}>{formatDashboardDate(lead.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className={styles.cardList} aria-label="Leads list (compact view)">
        {leads.map((lead) => (
          <li key={lead.id} className={styles.cardItem} data-testid="leads-list-card">
            <div className={styles.cardTop}>
              <div className={styles.cardTitleBlock}>
                <LeadSummaryCell lead={lead} />
              </div>
              <div className={styles.cardBadges}>
                <LeadPipelineBadge status={lead.status} />
                <LeadTemperatureBadge temperature={lead.temperature} />
              </div>
            </div>
            <dl className={styles.cardMeta}>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.leads.colScore") as string}</dt>
                <dd data-testid="lead-score-card">{formatScoreDisplay(lead.leadScore)}</dd>
              </div>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.leads.colNiche") as string}</dt>
                <dd>{lead.nicheLabel}</dd>
              </div>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.leads.colPhone") as string}</dt>
                <dd>{formatPhoneDisplay(lead.phone)}</dd>
              </div>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.leads.colCreated") as string}</dt>
                <dd>{formatDashboardDate(lead.createdAt)}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>

      {hasMore ? (
        <div className={styles.loadMoreRow}>
          <button
            className={styles.loadMoreBtn}
            onClick={onLoadMore}
            disabled={loadingMore}
            aria-label={t("dashboard.leads.loadMore") as string}
          >
            {loadingMore
              ? (t("dashboard.leads.loadingMore") as string)
              : (t("dashboard.leads.loadMore") as string)}
          </button>
        </div>
      ) : null}
    </div>
  );
}
