import type { CreateBotDraft } from "./types";

export type ExpectedCreateOutcome = {
  label: string;
  detail: string;
};

/** UX copy only — server is authoritative (matches these rules). */
export function expectedOutcomeAfterCreate(draft: CreateBotDraft): ExpectedCreateOutcome {
  const ch = draft.channel.preferredChannelId;
  const token = (draft.channel.telegramBotToken ?? "").trim();

  if (ch === "website_widget") {
    return {
      label: "Active (web)",
      detail: "No Telegram token required. The bot can be used from the website widget path once you embed it.",
    };
  }
  if (ch === "telegram" || ch === "both") {
    if (token.length >= 10) {
      return {
        label: "Active (if Telegram accepts the token)",
        detail:
          "We verify the token and register the webhook on the server. If Telegram or webhook setup fails, you’ll see an error instead of a false success.",
      };
    }
    return {
      label: "Channel pending",
      detail:
        "Saved without a Telegram token. Finish setup from the bot’s Telegram panel — the bot will not be active until a valid token and webhook succeed.",
    };
  }
  return {
    label: "Draft",
    detail: "Choose a channel to see the outcome.",
  };
}
