import { afterEach, describe, expect, it } from "vitest";

import { isSupportedNicheId } from "./constants";
import { setNicheCatalogCache } from "./niche-catalog-cache";
import type { NicheCatalogItemDto } from "@/lib/api/niche-catalog";

describe("isSupportedNicheId", () => {
  afterEach(() => {
    setNicheCatalogCache(null);
  });

  it("accepts fallback ids when catalog cache is empty", () => {
    expect(isSupportedNicheId("education")).toBe(true);
    expect(isSupportedNicheId("healthcare")).toBe(true);
    expect(isSupportedNicheId("unknown_xyz")).toBe(false);
  });

  it("tracks API catalog when cache is populated (rejects stale ids)", () => {
    const custom: NicheCatalogItemDto = {
      id: "custom_vertical",
      display_name: "Custom",
      description: "D",
      wizard_hint: "H",
      icon_key: "briefcase",
      supported_goals: ["support"],
      onboarding_hints: [],
      visible: true,
    };
    setNicheCatalogCache({ schema_version: 1, niches: [custom] });
    expect(isSupportedNicheId("custom_vertical")).toBe(true);
    expect(isSupportedNicheId("education")).toBe(false);
  });
});
