"use client";

import Link from "next/link";
import type { ReactElement } from "react";

import { useLanguage } from "@/contexts/language-context";

import styles from "./overview.module.css";

function IconInbox() {
  return (
    <svg className={styles.panelEmptyIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
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
  );
}

function IconUsers() {
  return (
    <svg className={styles.panelEmptyIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M12.5 7a4 4 0 1 0-4 4 4 4 0 0 0 4-4Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconSignal() {
  return (
    <svg className={styles.panelEmptyIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 19V5M9 19V9M14 19v-6M19 19v-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

type EmptyPanelProps = {
  title: string;
  viewAllHref: string;
  viewAllLabel: string;
  emptyTitle: string;
  emptyBody: string;
  Icon: () => ReactElement;
};

function EmptyPanel({ title, viewAllHref, viewAllLabel, emptyTitle, emptyBody, Icon }: EmptyPanelProps) {
  return (
    <div className={styles.panel}>
      <div className={styles.panelHead}>
        <h3 className={styles.panelTitle}>{title}</h3>
        <Link href={viewAllHref} className={styles.panelLink}>
          {viewAllLabel}
        </Link>
      </div>
      <div className={styles.panelEmpty}>
        <Icon />
        <p className={styles.panelEmptyTitle}>{emptyTitle}</p>
        <p className={styles.panelEmptyBody}>{emptyBody}</p>
      </div>
    </div>
  );
}

export function OverviewPanels() {
  const { t } = useLanguage();
  const openLabel = t("dashboard.overview.open") as string;

  return (
    <section aria-labelledby="overview-activity-heading">
      <p id="overview-activity-heading" className={styles.sectionLabel}>
        {t("dashboard.overview.activity") as string}
      </p>
      <div className={styles.panelsGrid}>
        <EmptyPanel
          title={t("dashboard.overview.recentBots") as string}
          viewAllHref="/dashboard/bots"
          viewAllLabel={openLabel}
          Icon={IconInbox}
          emptyTitle={t("dashboard.overview.recentBotsEmpty") as string}
          emptyBody={t("dashboard.overview.recentBotsEmptyHint") as string}
        />
        <EmptyPanel
          title={t("dashboard.overview.recentLeads") as string}
          viewAllHref="/dashboard/leads"
          viewAllLabel={openLabel}
          Icon={IconUsers}
          emptyTitle={t("dashboard.overview.recentLeadsEmpty") as string}
          emptyBody={t("dashboard.overview.recentLeadsEmptyHint") as string}
        />
        <EmptyPanel
          title={t("dashboard.overview.channelStatus") as string}
          viewAllHref="/dashboard/bots"
          viewAllLabel={openLabel}
          Icon={IconSignal}
          emptyTitle={t("dashboard.overview.channelStatusEmpty") as string}
          emptyBody={t("dashboard.overview.channelStatusEmptyHint") as string}
        />
      </div>
    </section>
  );
}
