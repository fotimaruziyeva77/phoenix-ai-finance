import { afterEach, describe, expect, it } from "vitest";

import { setNicheCatalogCache } from "./niche-catalog-cache";
import { toFriendlyNicheLabel } from "./labels";
import type { NicheCatalogItemDto } from "@/lib/api/niche-catalog";

describe("toFriendlyNicheLabel", () => {
  afterEach(() => setNicheCatalogCache(null));

  it("uses fallback display names when cache is empty", () => {
    expect(toFriendlyNicheLabel("education")).toBe("Education");
    expect(toFriendlyNicheLabel("healthcare")).toBe("Healthcare / Clinic");
    expect(toFriendlyNicheLabel("unknown")).toBe("unknown");
  });

  it("prefers catalog display_name when cache is set", () => {
    const row: NicheCatalogItemDto = {
      id: "education",
      display_name: "Edu API Label",
      description: "",
      wizard_hint: "",
      icon_key: "graduation-cap",
      supported_goals: [],
      onboarding_hints: [],
      visible: true,
    };
    setNicheCatalogCache({ schema_version: 1, niches: [row] });
    expect(toFriendlyNicheLabel("education")).toBe("Edu API Label");
  });
});
