import type { CreateBotDraft } from "./types";

import { WIZARD_STEPS } from "./steps-config";
import { isSupportedGoalType, isSupportedNicheId } from "@/lib/bot-domain/constants";

export type StepValidation = {
  ok: boolean;
  message: string | null;
};

function needsTelegramToken(draft: CreateBotDraft): boolean {
  const ch = draft.channel.preferredChannelId;
  return ch === "telegram" || ch === "both";
}

/**
 * Validate the current step only — keeps UX focused and forms uncluttered.
 */
export function validateStep(stepIndex: number, draft: CreateBotDraft): StepValidation {
  const meta = WIZARD_STEPS[stepIndex];
  if (!meta) {
    return { ok: false, message: "Invalid step." };
  }

  switch (meta.id) {
    case "niche":
      if (!isSupportedNicheId(draft.nicheId)) {
        return { ok: false, message: "Choose a niche to continue." };
      }
      return { ok: true, message: null };

    case "goal":
      if (!isSupportedGoalType(draft.goalId)) {
        return { ok: false, message: "Choose a goal to continue." };
      }
      return { ok: true, message: null };

    case "basics": {
      const name = draft.basics.displayName.trim();
      if (name.length < 2) {
        return { ok: false, message: "Enter a bot name (at least 2 characters)." };
      }
      return { ok: true, message: null };
    }

    case "channel": {
      if (!draft.channel.preferredChannelId) {
        return { ok: false, message: "Choose where this bot will be used to continue." };
      }
      if (needsTelegramToken(draft)) {
        const tok = (draft.channel.telegramBotToken ?? "").trim();
        if (tok.length > 0 && tok.length < 10) {
          return { ok: false, message: "Telegram token looks too short — paste the full token from BotFather." };
        }
      }
      return { ok: true, message: null };
    }

    case "knowledge":
      return { ok: true, message: null };

    case "review": {
      for (let i = 0; i < WIZARD_STEPS.length; i += 1) {
        const step = WIZARD_STEPS[i];
        if (!step || step.id === "review") break;
        const v = validateStep(i, draft);
        if (!v.ok) {
          return { ok: false, message: v.message ?? "Complete earlier steps before creating the bot." };
        }
      }
      return { ok: true, message: null };
    }
  }
}
