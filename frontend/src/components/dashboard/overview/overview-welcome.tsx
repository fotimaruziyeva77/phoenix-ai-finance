"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./overview.module.css";

type Props = {
  greetingName: string;
};

export function OverviewWelcome({ greetingName }: Props) {
  const { t } = useLanguage();
  const hi = t("dashboard.overview.hi") as string;
  const hiAnon = t("dashboard.overview.hiAnon") as string;

  const title = greetingName.trim() ? `${hi}, ${greetingName.trim()}` : hiAnon;

  return (
    <section className={styles.welcome} aria-labelledby="overview-welcome-heading">
      <h2 id="overview-welcome-heading" className={styles.welcomeTitle}>
        {title}
      </h2>
      <p className={styles.welcomeLead}>
        {t("dashboard.overview.welcomeLead") as string}
      </p>
      <p className={styles.sectionLabel}>
        {t("dashboard.overview.suggestedSteps") as string}
      </p>
      <ol className={styles.nextSteps}>
        <li>{t("dashboard.overview.step1") as string}</li>
        <li>{t("dashboard.overview.step2") as string}</li>
        <li>{t("dashboard.overview.step3") as string}</li>
      </ol>
    </section>
  );
}
