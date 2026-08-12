import { describe, expect, it } from "vitest";

import { knowledgeStatusDescription, knowledgeStatusLabel, knowledgeStatusVariant } from "./status";

describe("knowledge status presentation", () => {
  it("maps API statuses to clear labels", () => {
    expect(knowledgeStatusLabel("uploaded")).toBe("Queued");
    expect(knowledgeStatusLabel("processing")).toBe("Processing");
    expect(knowledgeStatusLabel("ready")).toBe("Ready");
    expect(knowledgeStatusLabel("failed")).toBe("Failed");
  });

  it("uses stable variants for styling", () => {
    expect(knowledgeStatusVariant("uploaded")).toBe("queued");
    expect(knowledgeStatusVariant("processing")).toBe("progress");
    expect(knowledgeStatusVariant("ready")).toBe("ready");
    expect(knowledgeStatusVariant("failed")).toBe("failed");
  });

  it("provides non-empty descriptions for tooltips", () => {
    for (const s of ["uploaded", "processing", "ready", "failed"] as const) {
      expect(knowledgeStatusDescription(s).length).toBeGreaterThan(4);
    }
  });
});
