import { CREATE_BOT_DRAFT_VERSION, type CreateBotDraft } from "./types";

import { createDefaultDraft } from "./default-draft";
import { isSupportedGoalType, isSupportedNicheId } from "@/lib/bot-domain/constants";

const STORAGE_KEY = "botforge_create_bot_draft_v2";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

const CHANNEL_IDS = new Set<string>(["website_widget", "telegram", "both"]);

function parseDraft(raw: unknown): CreateBotDraft | null {
  if (!isRecord(raw)) return null;
  if (raw.version !== CREATE_BOT_DRAFT_VERSION) return null;
  const nicheId =
    typeof raw.nicheId === "string" && isSupportedNicheId(raw.nicheId) ? raw.nicheId : null;
  const goalId = typeof raw.goalId === "string" && isSupportedGoalType(raw.goalId) ? raw.goalId : null;
  const basics = isRecord(raw.basics) ? raw.basics : null;
  const knowledge = isRecord(raw.knowledge) ? raw.knowledge : null;
  const channel = isRecord(raw.channel) ? raw.channel : null;
  if (!basics || !knowledge || !channel) return null;

  const pref = channel.preferredChannelId;
  const preferredChannelId =
    typeof pref === "string" && CHANNEL_IDS.has(pref)
      ? (pref as CreateBotDraft["channel"]["preferredChannelId"])
      : null;

  return {
    version: CREATE_BOT_DRAFT_VERSION,
    nicheId,
    goalId,
    basics: {
      displayName: typeof basics.displayName === "string" ? basics.displayName : "",
      languageCode: typeof basics.languageCode === "string" ? basics.languageCode : "en",
      toneId: typeof basics.toneId === "string" || basics.toneId === null ? basics.toneId : null,
      welcomeMessage:
        typeof basics.welcomeMessage === "string" ? basics.welcomeMessage : "",
      shortDescription:
        typeof basics.shortDescription === "string" ? basics.shortDescription : "",
    },
    channel: {
      preferredChannelId,
      telegramBotToken: "",
    },
    knowledge: {
      skipped: Boolean(knowledge.skipped),
      notes: typeof knowledge.notes === "string" ? knowledge.notes : "",
    },
  };
}

export function loadDraft(): CreateBotDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    return parseDraft(parsed);
  } catch {
    return null;
  }
}

/** Persist draft without Telegram token (never store secrets in localStorage). */
export function saveDraft(draft: CreateBotDraft): void {
  if (typeof window === "undefined") return;
  try {
    const safe: CreateBotDraft = {
      ...draft,
      channel: { ...draft.channel, telegramBotToken: "" },
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(safe));
  } catch {
    /* quota / private mode */
  }
}

export function clearDraft(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Safe default when storage is empty or invalid. */
export function loadDraftOrDefault(): CreateBotDraft {
  return loadDraft() ?? createDefaultDraft();
}
