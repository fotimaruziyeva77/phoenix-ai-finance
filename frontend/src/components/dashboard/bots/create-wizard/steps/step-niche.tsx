import { NicheIconByKey } from "@/components/niche/niche-icon-by-key";
import { useNicheCatalog } from "@/contexts/niche-catalog-context";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  updateDraft: (fn: (d: CreateBotDraft) => CreateBotDraft) => void;
  t: TFn;
};

export function StepNiche({ draft, updateDraft, t }: Props) {
  const { status, niches, usingEmergencyFallback } = useNicheCatalog();

  if (status === "loading" || status === "idle") {
    return (
      <div data-testid="niche-step-loading" className={styles.hintBox} aria-busy="true">
        {t("dashboard.wizard.nicheLoading") as string}
      </div>
    );
  }

  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.legend}>{t("dashboard.wizard.nicheLegend") as string}</legend>
      {usingEmergencyFallback ? (
        <p className={styles.hintBox} role="status" data-testid="niche-catalog-fallback-banner">
          {t("dashboard.wizard.nicheFallback") as string}
        </p>
      ) : null}
      <div className={styles.grid} data-testid="niche-grid">
        {niches.map((opt) => (
          <label key={opt.id} className={styles.choice} data-testid={`niche-card-${opt.id}`}>
            <input
              className={styles.choiceInput}
              type="radio"
              name="niche"
              value={opt.id}
              checked={draft.nicheId === opt.id}
              onChange={() =>
                updateDraft((d) => ({
                  ...d,
                  nicheId: opt.id,
                }))
              }
            />
            <span className={styles.choiceCard} data-selected={draft.nicheId === opt.id ? "true" : "false"}>
              <span className={styles.choiceIcon} aria-hidden>
                <NicheIconByKey iconKey={opt.icon_key} />
              </span>
              <span className={styles.choiceLabel}>{opt.display_name}</span>
              <p className={styles.choiceHint}>{opt.wizard_hint}</p>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
