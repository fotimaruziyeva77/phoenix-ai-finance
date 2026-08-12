"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./overview.module.css";

function IconBot() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="5" y="8" width="6" height="10" rx="2" stroke="currentColor" strokeWidth="1.75" />
      <rect x="13" y="5" width="6" height="13" rx="2" stroke="currentColor" strokeWidth="1.75" />
    </svg>
  );
}

function IconBook() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <path
        d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconChannel() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

type ActionItem = {
  href: string;
  titleKey: string;
  hintKey: string;
  Icon: () => React.ReactElement;
  testId: string;
};

const ACTIONS: ActionItem[] = [
  {
    href: "/dashboard/bots",
    titleKey: "dashboard.overview.createBot",
    hintKey: "dashboard.overview.createBotHint",
    Icon: IconBot,
    testId: "overview-action-bots",
  },
  {
    href: "/dashboard/bots",
    titleKey: "dashboard.overview.uploadKnowledge",
    hintKey: "dashboard.overview.uploadKnowledgeHint",
    Icon: IconBook,
    testId: "overview-action-knowledge",
  },
  {
    href: "/dashboard/bots",
    titleKey: "dashboard.overview.connectChannel",
    hintKey: "dashboard.overview.connectChannelHint",
    Icon: IconChannel,
    testId: "overview-action-channels",
  },
];

export function OverviewQuickActions() {
  const { t } = useLanguage();

  return (
    <section aria-labelledby="overview-quick-heading" data-testid="overview-quick-actions">
      <p id="overview-quick-heading" className={styles.sectionLabel}>
        {t("dashboard.overview.quickActions") as string}
      </p>
      <div className={styles.quickGrid}>
        {ACTIONS.map(({ href, titleKey, hintKey, Icon, testId }) => (
          <Link
            key={testId}
            href={href}
            className={styles.quickCard}
            data-testid={testId}
          >
            <span className={styles.quickIcon}>
              <Icon />
            </span>
            <h3 className={styles.quickTitle}>{t(titleKey) as string}</h3>
            <p className={styles.quickHint}>{t(hintKey) as string}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
