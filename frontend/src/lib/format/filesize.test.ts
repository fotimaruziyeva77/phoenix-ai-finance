import { describe, expect, it } from "vitest";

import { formatFileSizeBytes } from "./filesize";

describe("formatFileSizeBytes", () => {
  it("formats bytes and common steps", () => {
    expect(formatFileSizeBytes(0)).toBe("0 B");
    expect(formatFileSizeBytes(500)).toBe("500 B");
    expect(formatFileSizeBytes(1536)).toMatch(/KB/);
    expect(formatFileSizeBytes(5 * 1024 * 1024)).toMatch(/MB/);
  });

  it("guards invalid input", () => {
    expect(formatFileSizeBytes(-1)).toBe("—");
    expect(formatFileSizeBytes(Number.NaN)).toBe("—");
  });
});
