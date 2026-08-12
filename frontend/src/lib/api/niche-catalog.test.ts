import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/lib/api/client";

import { fetchNicheCatalog } from "./niche-catalog";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

describe("fetchNicheCatalog", () => {
  afterEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("returns typed envelope from GET /catalog/niches", async () => {
    const body = {
      schema_version: 1,
      niches: [
        {
          id: "education",
          display_name: "Education",
          description: "Desc",
          wizard_hint: "Hint",
          icon_key: "graduation-cap",
          supported_goals: ["support", "sales", "faq", "consulting"],
          onboarding_hints: [],
          visible: true,
        },
      ],
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(body);
    await expect(fetchNicheCatalog()).resolves.toEqual(body);
    expect(apiFetch).toHaveBeenCalledWith("/api/v1/catalog/niches");
  });
});
