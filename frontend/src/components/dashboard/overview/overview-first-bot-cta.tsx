"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./overview.module.css";

export function OverviewFirstBotCta() {
  const { t } = useLanguage();

  return (
    <section className={styles.firstBot} aria-labelledby="first-bot-heading">
      <div className={styles.firstBotInner}>
        <div>
          <h2 id="first-bot-heading" className={styles.firstBotTitle}>
            {t("dashboard.overview.createFirst") as string}
          </h2>
          <p className={styles.firstBotBody}>
            {t("dashboard.overview.createFirstBody") as string}
          </p>
        </div>
        <Link href="/dashboard/bots" className={styles.primaryCta}>
          {t("dashboard.overview.createFirstBtn") as string}
        </Link>
      </div>
    </section>
  );
}
