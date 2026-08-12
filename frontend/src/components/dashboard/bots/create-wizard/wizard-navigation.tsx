import Link from "next/link";

import styles from "./create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  stepIndex: number;
  isLastStep: boolean;
  skippable: boolean;
  isSubmitting: boolean;
  onBack: () => void;
  onNext: () => void;
  onSkip: () => void;
  onFinish: () => void;
  t: TFn;
};

export function WizardNavigation({
  stepIndex,
  isLastStep,
  skippable,
  isSubmitting,
  onBack,
  onNext,
  onSkip,
  onFinish,
  t,
}: Props) {
  const showBack = stepIndex > 0;

  return (
    <nav className={styles.nav} aria-label="Wizard steps" data-testid="wizard-navigation">
      <div className={styles.navCluster}>
        {showBack ? (
          <button type="button" className={`${styles.btn} ${styles.btnSecondary}`} onClick={onBack} disabled={isSubmitting}>
            {t("dashboard.wizard.back") as string}
          </button>
        ) : (
          <Link href="/dashboard/bots" className={`${styles.btn} ${styles.btnGhost}`}>
            {t("dashboard.wizard.exitToBots") as string}
          </Link>
        )}
      </div>

      <div className={styles.navSpacer} aria-hidden />

      <div className={styles.navCluster}>
        {skippable ? (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnGhost}`}
            onClick={onSkip}
            data-testid="wizard-nav-skip"
            disabled={isSubmitting}
          >
            {t("dashboard.wizard.skipForNow") as string}
          </button>
        ) : null}
        {isLastStep ? (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnPrimary}`}
            onClick={onFinish}
            data-testid="wizard-nav-finish"
            disabled={isSubmitting}
          >
            {isSubmitting ? (t("dashboard.wizard.creatingBot") as string) : (t("dashboard.wizard.createBot") as string)}
          </button>
        ) : (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnPrimary}`}
            onClick={onNext}
            data-testid="wizard-nav-next"
            disabled={isSubmitting}
          >
            {t("dashboard.wizard.continue") as string}
          </button>
        )}
      </div>
    </nav>
  );
}
