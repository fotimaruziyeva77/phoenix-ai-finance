"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./bots-dashboard.module.css";

export function BotsPageHeader() {
  const { t } = useLanguage();

  return (
    <header className={styles.pageHeader}>
      <div className={styles.pageHeaderText}>
        <h2 className={styles.pageTitle}>{t("dashboard.bots.title") as string}</h2>
        <p className={styles.pageSubtitle}>{t("dashboard.bots.subtitle") as string}</p>
      </div>
      <Link href="/dashboard/bots/new" className={styles.headerCreateBtn} data-testid="bots-header-create">
        {t("dashboard.bots.createBtn") as string}
      </Link>
    </header>
  );
}
