import { describe, expect, it } from "vitest";

import { createDefaultDraft } from "./default-draft";
import { expectedOutcomeAfterCreate } from "./expected-status";

describe("expectedOutcomeAfterCreate", () => {
  it("describes web as active path", () => {
    const draft = {
      ...createDefaultDraft(),
      channel: { preferredChannelId: "website_widget" as const, telegramBotToken: "" },
    };
    const o = expectedOutcomeAfterCreate(draft);
    expect(o.label).toContain("Active");
  });

  it("describes telegram without token as channel pending", () => {
    const draft = {
      ...createDefaultDraft(),
      channel: { preferredChannelId: "telegram" as const, telegramBotToken: "" },
    };
    const o = expectedOutcomeAfterCreate(draft);
    expect(o.label).toContain("Channel pending");
  });
});
