"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./bots-dashboard.module.css";

type Props = {
  endpointUnavailable?: boolean;
};

export function BotsEmptyState({ endpointUnavailable = false }: Props) {
  const { t } = useLanguage();

  return (
    <div className={styles.emptyWrap} data-testid="bots-empty-state">
      <div className={styles.emptyCard}>
        <div className={styles.emptyIcon} aria-hidden>
          <svg viewBox="0 0 24 24" fill="none" className={styles.emptySvg}>
            <path
              d="M12 3v3m0 12v3M4.5 9h3m9 0h3M7 7.5l2 2m6 0l2-2M7 16.5l2-2m6 0l2 2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </div>
        <h3 className={styles.emptyHeading}>{t("dashboard.bots.emptyTitle") as string}</h3>
        <p className={styles.emptyLead}>{t("dashboard.bots.emptyBody") as string}</p>
        {endpointUnavailable ? (
          <p className={styles.emptyNote} data-testid="bots-endpoint-unavailable">
            {t("dashboard.bots.emptyApiNote") as string}
          </p>
        ) : null}
        <Link href="/dashboard/bots/new" className={styles.emptyCta} data-testid="bots-empty-create">
          {t("dashboard.bots.emptyCta") as string}
        </Link>
      </div>
    </div>
  );
}
