import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { WorkspaceBot } from "@/lib/api/bots";

import { BotsList } from "./bots-list";

const SAMPLE_BOT: WorkspaceBot = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Support",
  nicheId: "services",
  nicheLabel: "Services",
  goalType: "support",
  goalLabel: "Support",
  status: "active",
  updatedAt: "2026-03-01T12:00:00.000Z",
};

describe("BotsList", () => {
  it("exposes table columns for name, niche, goal, status, and last updated", () => {
    const html = renderToStaticMarkup(<BotsList bots={[SAMPLE_BOT]} />);
    expect(html).toContain('data-testid="bots-list"');
    expect(html).toContain("Name");
    expect(html).toContain("Niche");
    expect(html).toContain("Goal");
    expect(html).toContain("Status");
    expect(html).toContain("Last updated");
    expect(html).toContain("Support");
    expect(html).toContain("Services");
    expect(html).toContain('data-testid="bots-list-row"');
  });

  it("renders compact cards for small screens (same data contract)", () => {
    const html = renderToStaticMarkup(<BotsList bots={[SAMPLE_BOT]} />);
    expect(html).toContain('data-testid="bots-list-card"');
  });
});
