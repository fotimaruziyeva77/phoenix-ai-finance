"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./bots-dashboard.module.css";

export function BotsListSkeleton() {
  const { t } = useLanguage();

  return (
    <div className={styles.skeletonWrap} role="status" aria-busy="true" aria-live="polite" data-testid="bots-list-skeleton">
      <span className={styles.visuallyHidden}>{t("dashboard.bots.loading") as string}</span>
      <div className={styles.skeletonRow} />
      <div className={styles.skeletonRow} />
      <div className={styles.skeletonRow} />
    </div>
  );
}
