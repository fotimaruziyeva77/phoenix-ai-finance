import { describe, expect, it } from "vitest";

import { getWorkspaceOverviewState } from "./workspace-overview";

describe("getWorkspaceOverviewState", () => {
  it("returns empty-first snapshot until API exists", () => {
    expect(getWorkspaceOverviewState()).toEqual({ hasBots: false });
  });
});
