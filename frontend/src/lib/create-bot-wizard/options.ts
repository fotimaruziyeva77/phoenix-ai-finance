/** Preset options — niche cards come from ``GET /api/v1/catalog/niches``. */

import type { SupportedGoalType } from "@/lib/bot-domain/constants";

export const GOAL_OPTIONS = [
  {
    id: "support" satisfies SupportedGoalType,
    label: "Support",
    hint: "Resolve issues fast with guided troubleshooting and escalation.",
  },
  {
    id: "sales" satisfies SupportedGoalType,
    label: "Sales",
    hint: "Convert visitors into leads with qualification and next-step prompts.",
  },
  {
    id: "faq" satisfies SupportedGoalType,
    label: "FAQ",
    hint: "Answer common questions with concise, reliable responses.",
  },
  {
    id: "consulting" satisfies SupportedGoalType,
    label: "Consulting",
    hint: "Collect context and deliver expert-style recommendations.",
  },
] as const;

export const TONE_OPTIONS = [
  { id: "friendly", label: "Friendly & concise" },
  { id: "professional", label: "Professional & formal" },
  { id: "playful", label: "Playful & light" },
  { id: "neutral", label: "Neutral & factual" },
] as const;

export const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
] as const;

export const CHANNEL_PLACEHOLDERS = [
  {
    id: "website_widget",
    label: "Website widget",
    hint: "No Telegram token required — bot can be active for the web channel.",
  },
  {
    id: "telegram",
    label: "Telegram",
    hint: "Requires a valid BotFather token before the bot can be active.",
  },
  {
    id: "both",
    label: "Both",
    hint: "Web can go active; Telegram still needs a verified token and webhook.",
  },
] as const;
