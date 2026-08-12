import { GOAL_OPTIONS } from "@/lib/create-bot-wizard/options";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  updateDraft: (fn: (d: CreateBotDraft) => CreateBotDraft) => void;
  t: TFn;
};

const GOAL_LABEL_KEYS: Record<string, string> = {
  support: "dashboard.wizard.goalSupport",
  sales: "dashboard.wizard.goalSales",
  faq: "dashboard.wizard.goalFaq",
  consulting: "dashboard.wizard.goalConsulting",
};
const GOAL_HINT_KEYS: Record<string, string> = {
  support: "dashboard.wizard.goalSupportHint",
  sales: "dashboard.wizard.goalSalesHint",
  faq: "dashboard.wizard.goalFaqHint",
  consulting: "dashboard.wizard.goalConsultingHint",
};

export function StepGoal({ draft, updateDraft, t }: Props) {
  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.legend}>{t("dashboard.wizard.goalLegend") as string}</legend>
      <div className={styles.grid} data-testid="goal-grid">
        {GOAL_OPTIONS.map((opt) => (
          <label key={opt.id} className={styles.choice} data-testid={`goal-card-${opt.id}`}>
            <input
              className={styles.choiceInput}
              type="radio"
              name="goal"
              value={opt.id}
              checked={draft.goalId === opt.id}
              onChange={() =>
                updateDraft((d) => ({
                  ...d,
                  goalId: opt.id,
                }))
              }
            />
            <span className={styles.choiceCard} data-selected={draft.goalId === opt.id ? "true" : "false"}>
              <span className={styles.choiceLabel}>{t(GOAL_LABEL_KEYS[opt.id] ?? "") as string}</span>
              <p className={styles.choiceHint}>{t(GOAL_HINT_KEYS[opt.id] ?? "") as string}</p>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
