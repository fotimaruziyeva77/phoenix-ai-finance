import { describe, expect, it } from "vitest";

import { knowledgeFilesNeedPolling, knowledgeListNeedsPolling } from "./polling";

describe("knowledgeListNeedsPolling", () => {
  it("is true while any file is uploaded or processing", () => {
    expect(
      knowledgeListNeedsPolling([
        { processing_status: "ready" },
        { processing_status: "processing" },
      ]),
    ).toBe(true);
  });

  it("is false when all files are terminal", () => {
    expect(
      knowledgeListNeedsPolling([
        { processing_status: "ready" },
        { processing_status: "failed" },
      ]),
    ).toBe(false);
  });
});

describe("knowledgeFilesNeedPolling", () => {
  it("matches uploaded and processing only", () => {
    expect(knowledgeFilesNeedPolling("uploaded")).toBe(true);
    expect(knowledgeFilesNeedPolling("processing")).toBe(true);
    expect(knowledgeFilesNeedPolling("ready")).toBe(false);
    expect(knowledgeFilesNeedPolling("failed")).toBe(false);
  });
});
