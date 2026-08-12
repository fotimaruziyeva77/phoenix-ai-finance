import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const cssPath = join(dirname(fileURLToPath(import.meta.url)), "styles.css");

describe("widget responsive / layout CSS contract", () => {
  it("defines mobile breakpoint and core layout classes", () => {
    const css = readFileSync(cssPath, "utf8");
    expect(css).toMatch(/@media\s*\(\s*max-width:\s*480px\s*\)/);
    expect(css).toContain(".bfw-panel");
    expect(css).toContain(".bfw-launcher");
    expect(css).toContain("min(");
    expect(css).toContain("100vw");
  });
});
