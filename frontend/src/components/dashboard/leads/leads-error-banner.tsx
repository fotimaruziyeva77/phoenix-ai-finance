"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./leads-dashboard.module.css";

type Props = {
  message: string;
  onRetry: () => void;
};

export function LeadsErrorBanner({ message, onRetry }: Props) {
  const { t } = useLanguage();

  return (
    <div className={styles.errorBanner} role="alert" data-testid="leads-error-banner">
      <p className={styles.errorText}>{message}</p>
      <button type="button" className={styles.retryBtn} onClick={onRetry}>
        {t("dashboard.leads.retry") as string}
      </button>
    </div>
  );
}
