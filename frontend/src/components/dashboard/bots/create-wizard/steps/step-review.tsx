import { toFriendlyGoalLabel, toFriendlyNicheLabel } from "@/lib/bot-domain/labels";
import { CHANNEL_PLACEHOLDERS } from "@/lib/create-bot-wizard/options";
import { expectedOutcomeAfterCreate } from "@/lib/create-bot-wizard/expected-status";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  t: TFn;
  pendingFilesCount: number;
};

function channelLabel(id: CreateBotDraft["channel"]["preferredChannelId"]): string {
  if (!id) return "—";
  const row = CHANNEL_PLACEHOLDERS.find((c) => c.id === id);
  return row?.label ?? id;
}

function toneLabel(toneId: string | null): string {
  if (!toneId) return "—";
  return toneId.replace(/_/g, " ");
}

const OUTCOME_LABEL_KEYS: Record<string, string> = {
  "Active (web)": "dashboard.wizard.outcomeActiveWeb",
  "Active (if Telegram accepts the token)": "dashboard.wizard.outcomeActiveTg",
  "Channel pending": "dashboard.wizard.outcomePending",
  "Draft": "dashboard.wizard.outcomeDraft",
};
const OUTCOME_DETAIL_KEYS: Record<string, string> = {
  "Active (web)": "dashboard.wizard.outcomeActiveWebDetail",
  "Active (if Telegram accepts the token)": "dashboard.wizard.outcomeActiveTgDetail",
  "Channel pending": "dashboard.wizard.outcomePendingDetail",
  "Draft": "dashboard.wizard.outcomeDraftDetail",
};

export function StepReview({ draft, t, pendingFilesCount }: Props) {
  const outcome = expectedOutcomeAfterCreate(draft);
  const tokenEntered = (draft.channel.telegramBotToken ?? "").trim().length >= 10;

  return (
    <div className={styles.review} data-testid="wizard-step-review-content">
      <dl className={styles.reviewList}>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revNiche") as string}</dt>
          <dd>{draft.nicheId ? toFriendlyNicheLabel(draft.nicheId) : "—"}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revGoal") as string}</dt>
          <dd>{draft.goalId ? toFriendlyGoalLabel(draft.goalId) : "—"}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revName") as string}</dt>
          <dd>{draft.basics.displayName.trim() || "—"}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revLanguage") as string}</dt>
          <dd>{draft.basics.languageCode || "—"}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revTone") as string}</dt>
          <dd>{toneLabel(draft.basics.toneId)}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revChannel") as string}</dt>
          <dd>{channelLabel(draft.channel.preferredChannelId)}</dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revTelegramToken") as string}</dt>
          <dd data-testid="review-telegram-token-summary">
            {draft.channel.preferredChannelId === "website_widget"
              ? (t("dashboard.wizard.tokenNA") as string)
              : tokenEntered
                ? (t("dashboard.wizard.tokenProvided") as string)
                : (t("dashboard.wizard.tokenNotProvided") as string)}
          </dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revFiles") as string}</dt>
          <dd data-testid="review-files-summary">
            {pendingFilesCount > 0
              ? `${pendingFilesCount} ${t("dashboard.wizard.filesReady") as string}`
              : (t("dashboard.wizard.noFilesAttached") as string)}
          </dd>
        </div>
        <div className={styles.reviewRow}>
          <dt>{t("dashboard.wizard.revKnowledge") as string}</dt>
          <dd>
            {draft.knowledge.skipped
              ? (t("dashboard.wizard.knowledgeSkipped") as string)
              : draft.knowledge.notes.trim()
                ? draft.knowledge.notes.trim()
                : (t("dashboard.wizard.knowledgeNone") as string)}
          </dd>
        </div>
      </dl>

      <div className={styles.outcomeCallout} data-testid="review-expected-outcome">
        <p className={styles.outcomeTitle}>{t("dashboard.wizard.expectedStatus") as string}</p>
        <p className={styles.outcomeLabel}>{(t(OUTCOME_LABEL_KEYS[outcome.label] ?? "") as string) || outcome.label}</p>
        <p className={styles.outcomeDetail}>{(t(OUTCOME_DETAIL_KEYS[outcome.label] ?? "") as string) || outcome.detail}</p>
      </div>
    </div>
  );
}
