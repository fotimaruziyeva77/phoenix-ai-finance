import { describe, expect, it } from "vitest";

import { inferenceProviderLabel } from "./inference-provider-label";

describe("inferenceProviderLabel", () => {
  it("maps known provider ids to neutral labels", () => {
    expect(inferenceProviderLabel("gemini")).toBe("Built-in default");
  });

  it("falls back to the raw id for unknown providers", () => {
    expect(inferenceProviderLabel("future-provider")).toBe("future-provider");
  });
});
