import type { NicheId, SupportedGoalType } from "@/lib/bot-domain/constants";

/**
 * Create-bot wizard draft — versioned for local persistence.
 */
export const CREATE_BOT_DRAFT_VERSION = 2 as const;

export type ChannelChoiceId = "website_widget" | "telegram" | "both";

export type CreateBotDraft = {
  version: typeof CREATE_BOT_DRAFT_VERSION;
  nicheId: NicheId | null;
  goalId: SupportedGoalType | null;
  basics: {
    displayName: string;
    languageCode: string;
    toneId: string | null;
    /** Short line shown when the bot opens a chat (optional). */
    welcomeMessage: string;
    /** Internal summary for teammate context and future list views (optional). */
    shortDescription: string;
  };
  channel: {
    /** User must pick one channel strategy before continuing. */
    preferredChannelId: ChannelChoiceId | null;
    /**
     * BotFather token when Telegram or Both is selected. Never persisted to localStorage
     * (see draft-storage); session memory only.
     */
    telegramBotToken: string;
  };
  knowledge: {
    skipped: boolean;
    /** Freeform notes; file uploads happen post-create in the dashboard. */
    notes: string;
  };
};

export type WizardStepId = "niche" | "goal" | "basics" | "channel" | "knowledge" | "review";

export type WizardStepMeta = {
  id: WizardStepId;
  /** Short label for the stepper */
  label: string;
  /** Heading on the step panel */
  title: string;
  description: string;
  skippable: boolean;
  /** Optional transformer applied when user skips this step. */
  applySkip?: (draft: CreateBotDraft) => CreateBotDraft;
};
