import { WIZARD_STEPS } from "@/lib/create-bot-wizard/steps-config";

import styles from "./create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  stepIndex: number;
  t: TFn;
};

const STEP_LABEL_KEYS: Record<string, string> = {
  niche: "dashboard.wizard.stepNiche",
  goal: "dashboard.wizard.stepGoal",
  basics: "dashboard.wizard.stepBasics",
  channel: "dashboard.wizard.stepChannel",
  knowledge: "dashboard.wizard.stepKnowledge",
  review: "dashboard.wizard.stepReview",
};

/**
 * Read-only progress indicator — navigation is Next/Back only (no jumping ahead).
 */
export function WizardStepper({ stepIndex, t }: Props) {
  const currentNumber = Math.min(stepIndex + 1, WIZARD_STEPS.length);
  return (
    <>
      <p className={styles.stepperMeta} data-testid="wizard-stepper-meta">
        {t("dashboard.wizard.step") as string} {currentNumber} {t("dashboard.wizard.of") as string} {WIZARD_STEPS.length}
      </p>
      <ol className={styles.stepper} aria-label="Bot creation progress" data-testid="wizard-stepper">
        {WIZARD_STEPS.map((step, i) => {
        const done = i < stepIndex;
        const current = i === stepIndex;
        return (
          <li key={step.id} className={styles.stepperItem}>
            <span
              className={`${styles.stepperBtn} ${done ? styles.stepperBtnDone : ""} ${current ? styles.stepperBtnCurrent : ""}`}
              aria-current={current ? "step" : undefined}
            >
              <span className={styles.stepperIndex} aria-hidden>
                {i + 1}
              </span>
              {t(STEP_LABEL_KEYS[step.id] ?? "") as string}
            </span>
          </li>
        );
        })}
      </ol>
    </>
  );
}
