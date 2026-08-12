import { useMemo } from "react";

import { useNicheCatalog } from "@/contexts/niche-catalog-context";
import { LANGUAGE_OPTIONS, TONE_OPTIONS } from "@/lib/create-bot-wizard/options";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  updateDraft: (fn: (d: CreateBotDraft) => CreateBotDraft) => void;
  t: TFn;
};

const TONE_LABEL_KEYS: Record<string, string> = {
  friendly: "dashboard.wizard.toneFriendly",
  professional: "dashboard.wizard.toneProfessional",
  playful: "dashboard.wizard.tonePlayful",
  neutral: "dashboard.wizard.toneNeutral",
};

export function StepBasics({ draft, updateDraft, t }: Props) {
  const { niches } = useNicheCatalog();
  const welcomePlaceholder = useMemo(() => {
    const fallback = t("dashboard.wizard.defaultWelcome") as string;
    if (!draft.nicheId) return fallback;
    const niche = niches.find((n) => n.id === draft.nicheId);
    if (!niche?.default_welcome_messages) return fallback;
    const lang = (draft.basics.languageCode || "en").slice(0, 2).toLowerCase();
    return niche.default_welcome_messages[lang] ?? niche.default_welcome_messages["en"] ?? fallback;
  }, [draft.nicheId, draft.basics.languageCode, niches, t]);

  return (
    <>
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel} htmlFor="bot-display-name">
          {t("dashboard.wizard.botName") as string}
        </label>
        <p className={styles.fieldHelp}>{t("dashboard.wizard.botNameHelp") as string}</p>
        <input
          id="bot-display-name"
          className={styles.textInput}
          type="text"
          required
          minLength={2}
          aria-required="true"
          autoComplete="off"
          placeholder={t("dashboard.wizard.botNamePlaceholder") as string}
          value={draft.basics.displayName}
          onChange={(e) =>
            updateDraft((d) => ({
              ...d,
              basics: { ...d.basics, displayName: e.target.value },
            }))
          }
        />
      </div>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>{t("dashboard.wizard.toneLegend") as string}</legend>
        <p className={styles.fieldHelp}>
          {t("dashboard.wizard.toneHelp") as string}
        </p>
        <div className={styles.gridSingle}>
          {TONE_OPTIONS.map((opt) => (
            <label key={opt.id} className={styles.choice}>
              <input
                className={styles.choiceInput}
                type="radio"
                name="tone"
                value={opt.id}
                checked={draft.basics.toneId === opt.id}
                onChange={() =>
                  updateDraft((d) => ({
                    ...d,
                    basics: { ...d.basics, toneId: opt.id },
                  }))
                }
              />
              <span className={styles.choiceCard}>
                <span className={styles.choiceLabel}>{t(TONE_LABEL_KEYS[opt.id] ?? "") as string}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel} htmlFor="bot-language">
          {t("dashboard.wizard.languageLabel") as string} <span className={styles.optionalTag}>({t("dashboard.wizard.optional") as string})</span>
        </label>
        <p className={styles.fieldHelp}>
          {t("dashboard.wizard.languageHelp") as string}
        </p>
        <select
          id="bot-language"
          className={styles.textInput}
          value={draft.basics.languageCode}
          onChange={(e) =>
            updateDraft((d) => ({
              ...d,
              basics: { ...d.basics, languageCode: e.target.value },
            }))
          }
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt.code} value={opt.code}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel} htmlFor="bot-description">
          {t("dashboard.wizard.shortDesc") as string} <span className={styles.optionalTag}>({t("dashboard.wizard.optional") as string})</span>
        </label>
        <textarea
          id="bot-description"
          className={styles.textArea}
          placeholder={t("dashboard.wizard.shortDescPlaceholder") as string}
          value={draft.basics.shortDescription}
          onChange={(e) =>
            updateDraft((d) => ({
              ...d,
              basics: { ...d.basics, shortDescription: e.target.value },
            }))
          }
        />
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel} htmlFor="bot-welcome">
          {t("dashboard.wizard.openingLine") as string} <span className={styles.optionalTag}>({t("dashboard.wizard.optional") as string})</span>
        </label>
        <p className={styles.fieldHelp}>
          {t("dashboard.wizard.openingLineHelp") as string}
        </p>
        <textarea
          id="bot-welcome"
          className={styles.textArea}
          placeholder={welcomePlaceholder}
          value={draft.basics.welcomeMessage}
          onChange={(e) =>
            updateDraft((d) => ({
              ...d,
              basics: { ...d.basics, welcomeMessage: e.target.value },
            }))
          }
        />
      </div>
    </>
  );
}
