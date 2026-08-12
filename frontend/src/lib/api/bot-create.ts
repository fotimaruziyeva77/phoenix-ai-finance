import { apiFetchWithAuth } from "@/lib/api/client";
import {
  isSupportedGoalType,
  isSupportedNicheId,
  type NicheId,
  type SupportedGoalType,
} from "@/lib/bot-domain/constants";
import { mapChannelToInitialChannel } from "@/lib/create-bot-wizard/map-channel-to-api";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

export type CreateBotPayload = {
  name: string;
  niche_id: NicheId;
  goal_type: SupportedGoalType;
  welcome_message: string | null;
  tone: string | null;
  language: string | null;
  short_description: string | null;
  initial_channel: "web" | "telegram" | "both";
  telegram_bot_token?: string | null;
};

/** Normalized snapshot from POST /api/v1/bots (201) for honest success UI. */
export type BotCreateResult = {
  id: string;
  status: string;
  primary_channel: string | null;
  name: string;
};

function toNullableTrimmed(value: string): string | null {
  const v = value.trim();
  return v.length > 0 ? v : null;
}

/** Build the backend bot-create payload from wizard draft state. */
export function buildCreateBotPayload(draft: CreateBotDraft): CreateBotPayload {
  if (!isSupportedNicheId(draft.nicheId)) {
    throw new Error("Cannot build bot payload without a supported nicheId.");
  }
  if (!isSupportedGoalType(draft.goalId)) {
    throw new Error("Cannot build bot payload without goalId.");
  }
  const initial = mapChannelToInitialChannel(draft.channel.preferredChannelId);
  if (!initial) {
    throw new Error("Cannot build bot payload without channel.");
  }

  const tokenTrim = (draft.channel.telegramBotToken ?? "").trim();
  const payload: CreateBotPayload = {
    name: draft.basics.displayName.trim(),
    niche_id: draft.nicheId,
    goal_type: draft.goalId,
    welcome_message: toNullableTrimmed(draft.basics.welcomeMessage),
    tone: draft.basics.toneId,
    language: toNullableTrimmed(draft.basics.languageCode),
    short_description: toNullableTrimmed(draft.basics.shortDescription),
    initial_channel: initial,
  };
  if (initial !== "web" && tokenTrim.length >= 10) {
    payload.telegram_bot_token = tokenTrim;
  }
  return payload;
}

/** Real integration path for bot creation. */
export async function createBotFromWizard(
  accessToken: string | null,
  payload: CreateBotPayload,
): Promise<BotCreateResult> {
  return apiFetchWithAuth<BotCreateResult>("/api/v1/bots", accessToken, {
    method: "POST",
    body: payload,
  });
}
