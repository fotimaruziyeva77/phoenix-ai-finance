"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./leads-dashboard.module.css";

type Props = {
  filtered: boolean;
  endpointUnavailable: boolean;
};

export function LeadsEmptyState({ filtered, endpointUnavailable }: Props) {
  const { t } = useLanguage();

  if (endpointUnavailable) {
    return (
      <div className={styles.emptyWrap} data-testid="leads-empty-state">
        <div className={styles.emptyCard}>
          <div className={styles.emptyIcon} aria-hidden>
            <svg className={styles.emptySvg} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <h2 className={styles.emptyHeading}>{t("dashboard.leads.emptyApiTitle") as string}</h2>
          <p className={styles.emptyLead}>{t("dashboard.leads.emptyApiBody") as string}</p>
        </div>
      </div>
    );
  }

  if (filtered) {
    return (
      <div className={styles.emptyWrap} data-testid="leads-empty-filtered">
        <div className={styles.emptyCard}>
          <div className={styles.emptyIcon} aria-hidden>
            <svg className={styles.emptySvg} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
          </div>
          <h2 className={styles.emptyHeading}>{t("dashboard.leads.emptyFilterTitle") as string}</h2>
          <p className={styles.emptyLead}>{t("dashboard.leads.emptyFilterBody") as string}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.emptyWrap} data-testid="leads-empty-state">
      <div className={styles.emptyCard}>
        <div className={styles.emptyIcon} aria-hidden>
          <svg className={styles.emptySvg} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
          </svg>
        </div>
        <h2 className={styles.emptyHeading}>{t("dashboard.leads.emptyTitle") as string}</h2>
        <p className={styles.emptyLead}>{t("dashboard.leads.emptyBody") as string}</p>
        <Link href="/dashboard/bots" className={styles.emptyCta}>
          {t("dashboard.leads.emptyCta") as string}
        </Link>
      </div>
    </div>
  );
}
