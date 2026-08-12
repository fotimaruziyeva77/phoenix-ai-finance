import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UseWorkspaceBotsResult } from "@/hooks/useWorkspaceBots";

vi.mock("@/hooks/useWorkspaceBots", () => ({
  useWorkspaceBots: vi.fn(),
}));

import { useWorkspaceBots } from "@/hooks/useWorkspaceBots";

import { DashboardBots } from "./dashboard-bots";

function baseMock(overrides: Partial<UseWorkspaceBotsResult> = {}): UseWorkspaceBotsResult {
  return {
    status: "success",
    bots: [],
    endpointUnavailable: false,
    errorMessage: null,
    refetch: vi.fn(),
    ...overrides,
  };
}

describe("DashboardBots", () => {
  beforeEach(() => {
    vi.mocked(useWorkspaceBots).mockReturnValue(baseMock());
  });

  it("renders header, toolbar, empty state, and data region for list content", () => {
    const html = renderToStaticMarkup(<DashboardBots />);
    expect(html).toContain('data-testid="bots-page-root"');
    expect(html).toContain('data-testid="bots-data-region"');
    expect(html).toContain("Your bots");
    expect(html).toContain('data-testid="bots-header-create"');
    expect(html).toContain('data-testid="bots-search"');
    expect(html).toContain('data-testid="bots-empty-state"');
    expect(html).toContain('data-testid="bots-empty-create"');
    expect(html).not.toContain('data-testid="bots-list"');
  });

  it("renders list when workspace has bots", () => {
    vi.mocked(useWorkspaceBots).mockReturnValue(
      baseMock({
        bots: [
          {
            id: "1",
            name: "Support",
            nicheId: "services",
            nicheLabel: "Services",
            goalType: "support",
            goalLabel: "Support",
            status: "active",
            updatedAt: "2026-03-01T12:00:00.000Z",
          },
        ],
      }),
    );
    const html = renderToStaticMarkup(<DashboardBots />);
    expect(html).toContain('data-testid="bots-list"');
    expect(html).toContain("Support");
  });

  it("shows skeleton while loading", () => {
    vi.mocked(useWorkspaceBots).mockReturnValue(baseMock({ status: "loading" }));
    const html = renderToStaticMarkup(<DashboardBots />);
    expect(html).toContain('data-testid="bots-list-skeleton"');
  });
});
