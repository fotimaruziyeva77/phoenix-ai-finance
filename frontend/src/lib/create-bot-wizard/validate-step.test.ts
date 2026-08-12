import { describe, expect, it } from "vitest";

import { createDefaultDraft } from "./default-draft";
import { validateStep } from "./validate-step";

describe("validateStep", () => {
  it("requires niche on step 0", () => {
    const d = createDefaultDraft();
    expect(validateStep(0, d).ok).toBe(false);
    expect(validateStep(0, { ...d, nicheId: "services" }).ok).toBe(true);
  });

  it("requires goal on step 1", () => {
    const d = { ...createDefaultDraft(), nicheId: "services" };
    expect(validateStep(1, d).ok).toBe(false);
    expect(validateStep(1, { ...d, goalId: "support" }).ok).toBe(true);
  });

  it("requires name only on basics step", () => {
    const d = {
      ...createDefaultDraft(),
      nicheId: "services",
      goalId: "support",
    };
    expect(validateStep(2, d).ok).toBe(false);
    expect(validateStep(2, { ...d, basics: { ...d.basics, displayName: "A" } }).ok).toBe(false);
    expect(
      validateStep(2, {
        ...d,
        basics: { ...d.basics, displayName: "Helper" },
      }).ok,
    ).toBe(true);
  });

  it("requires channel selection on channel step; knowledge and review follow", () => {
    const base = {
      ...createDefaultDraft(),
      nicheId: "services",
      goalId: "support",
      basics: {
        displayName: "Helper",
        languageCode: "en",
        toneId: null,
        welcomeMessage: "",
        shortDescription: "",
      },
    };
    expect(validateStep(3, base).ok).toBe(false);
    const withChannel = {
      ...base,
      channel: { preferredChannelId: "website_widget" as const, telegramBotToken: "" },
    };
    expect(validateStep(3, withChannel).ok).toBe(true);
    expect(validateStep(4, withChannel).ok).toBe(true);
    expect(validateStep(5, withChannel).ok).toBe(true);
  });
});
