import { CREATE_BOT_DRAFT_VERSION, type CreateBotDraft } from "./types";

export function createDefaultDraft(): CreateBotDraft {
  return {
    version: CREATE_BOT_DRAFT_VERSION,
    nicheId: null,
    goalId: null,
    basics: {
      displayName: "",
      languageCode: "en",
      toneId: null,
      welcomeMessage: "",
      shortDescription: "",
    },
    channel: {
      preferredChannelId: null,
      telegramBotToken: "",
    },
    knowledge: {
      skipped: false,
      notes: "",
    },
  };
}
