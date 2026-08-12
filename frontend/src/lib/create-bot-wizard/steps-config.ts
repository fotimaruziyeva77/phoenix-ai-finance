import type { WizardStepMeta } from "./types";

export const WIZARD_STEPS: readonly WizardStepMeta[] = [
  {
    id: "niche",
    label: "Niche",
    title: "What is this bot for?",
    description: "Pick the context that best matches your business. You can refine details later.",
    skippable: false,
  },
  {
    id: "goal",
    label: "Goal",
    title: "What should the bot achieve?",
    description: "Choose a primary outcome so tone and flows stay aligned.",
    skippable: false,
  },
  {
    id: "basics",
    label: "Basics",
    title: "Name and voice",
    description: "Give your bot a clear name and how it should sound to visitors.",
    skippable: false,
  },
  {
    id: "channel",
    label: "Channel",
    title: "Where people will talk to you",
    description:
      "Website widget goes live without a Telegram token. Telegram (or both) needs a valid BotFather token before the bot can be active.",
    skippable: false,
  },
  {
    id: "knowledge",
    label: "Knowledge",
    title: "Ground answers in your content",
    description:
      "Optional notes only — documents are not uploaded in this wizard. Add files from the bot’s Knowledge base after creation.",
    skippable: true,
    applySkip: (draft) => ({
      ...draft,
      knowledge: { skipped: true, notes: "" },
    }),
  },
  {
    id: "review",
    label: "Review",
    title: "Review and create",
    description: "Confirm your choices. The status we create matches real backend rules — not a fake “ready” state.",
    skippable: false,
  },
] as const;
