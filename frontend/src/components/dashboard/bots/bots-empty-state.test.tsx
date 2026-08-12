import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BotsEmptyState } from "./bots-empty-state";

describe("BotsEmptyState", () => {
  it("renders strong empty copy and primary CTA to create first bot", () => {
    const html = renderToStaticMarkup(<BotsEmptyState />);
    expect(html).toContain('data-testid="bots-empty-state"');
    expect(html).toContain("No bots in this workspace yet");
    expect(html).toContain('data-testid="bots-empty-create"');
    expect(html).toContain("Create your first bot");
  });

  it("optionally surfaces API-unavailable hint without fake bot rows", () => {
    const html = renderToStaticMarkup(<BotsEmptyState endpointUnavailable />);
    expect(html).toContain('data-testid="bots-endpoint-unavailable"');
    expect(html).toContain("The bot list API is not reachable");
  });
});
