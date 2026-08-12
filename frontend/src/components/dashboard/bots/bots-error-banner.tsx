"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./bots-dashboard.module.css";

type Props = {
  message: string;
  onRetry: () => void;
};

export function BotsErrorBanner({ message, onRetry }: Props) {
  const { t } = useLanguage();

  return (
    <div className={styles.errorBanner} role="alert" aria-live="assertive" data-testid="bots-error-banner">
      <p className={styles.errorText}>{message}</p>
      <button type="button" className={styles.retryBtn} onClick={onRetry} aria-label={t("dashboard.bots.retry") as string}>
        {t("dashboard.bots.retry") as string}
      </button>
    </div>
  );
}
