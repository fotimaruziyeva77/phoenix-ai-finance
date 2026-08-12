import { describe, expect, it } from "vitest";

import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";

import { buildCreateBotPayload } from "./bot-create";

describe("buildCreateBotPayload", () => {
  it("combines wizard steps into backend-ready payload", () => {
    const draft = {
      ...createDefaultDraft(),
      nicheId: "education",
      goalId: "support",
      basics: {
        displayName: "Campus Bot",
        languageCode: "en",
        toneId: "friendly",
        welcomeMessage: "Hello students!",
        shortDescription: "Answers admissions and class schedule questions.",
      },
      knowledge: {
        skipped: false,
        notes: "Tuition FAQ and deadlines",
      },
      channel: {
        preferredChannelId: "website_widget" as const,
        telegramBotToken: "",
      },
    };

    expect(buildCreateBotPayload(draft)).toEqual({
      name: "Campus Bot",
      niche_id: "education",
      goal_type: "support",
      language: "en",
      tone: "friendly",
      welcome_message: "Hello students!",
      short_description: "Answers admissions and class schedule questions.",
      initial_channel: "web",
    });
  });

  it("rejects submit payload when niche/goal are not selected", () => {
    const draft = createDefaultDraft();
    expect(() => buildCreateBotPayload(draft)).toThrowError("Cannot build bot payload without nicheId.");

    const withNicheOnly = { ...draft, nicheId: "education" as const };
    expect(() => buildCreateBotPayload(withNicheOnly)).toThrowError("Cannot build bot payload without goalId.");
  });

  it("prevents invalid frontend-only values from submit mapping", () => {
    const draft = {
      ...createDefaultDraft(),
      nicheId: "frontend_only_niche",
      goalId: "frontend_only_goal",
      basics: {
        ...createDefaultDraft().basics,
        displayName: "Unsafe Bot",
      },
    };
    // simulate untrusted/local-storage-corrupted shape at runtime
    const unsafe = draft as unknown as Parameters<typeof buildCreateBotPayload>[0];
    expect(() => buildCreateBotPayload(unsafe)).toThrowError("Cannot build bot payload without nicheId.");
  });
});
