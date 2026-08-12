import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";
import { CHANNEL_PLACEHOLDERS } from "@/lib/create-bot-wizard/options";

import { StepChannel } from "./step-channel";

describe("StepChannel", () => {
  it("renders exactly 3 MVP channel options with brief explanations", () => {
    const html = renderToStaticMarkup(
      <StepChannel draft={createDefaultDraft()} updateDraft={vi.fn()} />,
    );
    expect(CHANNEL_PLACEHOLDERS).toHaveLength(3);
    expect(html).toContain("Website widget does not require a Telegram token.");
    for (const opt of CHANNEL_PLACEHOLDERS) {
      expect(html).toContain(`data-testid="channel-card-${opt.id}"`);
      expect(html).toContain(opt.label);
      expect(html).toContain(opt.hint);
    }
  });

  it("reflects selected channel state", () => {
    const draft = {
      ...createDefaultDraft(),
      channel: { preferredChannelId: "both", telegramBotToken: "" },
    };
    const html = renderToStaticMarkup(<StepChannel draft={draft} updateDraft={vi.fn()} />);
    expect(html).toContain('value="both"');
    expect(html).toContain("checked");
    expect(html).toContain('data-selected="true"');
  });
});
