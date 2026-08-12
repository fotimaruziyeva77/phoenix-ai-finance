import { expect, test } from "@playwright/test";

const EXPECTED_STEP_TITLES = [
  "Sign up",
  "Choose niche",
  "Upload knowledge (optional)",
  "Connect website or Telegram",
  "Start getting leads",
] as const;

test.describe("How it works section", () => {
  test("all step titles and descriptions are visible", async ({ page }) => {
    await page.goto("/#how-it-works");
    const section = page.locator("#how-it-works");
    await expect(section.getByRole("heading", { name: "How it works", level: 2 })).toBeVisible();

    const cards = section.locator("ol > li");
    await expect(cards).toHaveCount(5);

    for (const title of EXPECTED_STEP_TITLES) {
      await expect(section.getByRole("heading", { name: title, level: 3 })).toBeVisible();
    }

    await expect(section.getByText("Create your account and pick a workspace name.")).toBeVisible();
    await expect(section.getByText("Tell the bot what you sell and who you help.")).toBeVisible();
  });

  test("steps are in the correct order", async ({ page }) => {
    await page.goto("/");
    const titles = await page.locator("#how-it-works ol > li h3").allInnerTexts();
    const normalized = titles.map((t) => t.replace(/\s+/g, " ").trim());
    expect(normalized).toEqual([...EXPECTED_STEP_TITLES]);
  });

  test("responsive grid: stacked on narrow, row layout on wide", async ({ page }) => {
    await page.goto("/");
    const cards = page.locator("#how-it-works ol > li");

    await page.setViewportSize({ width: 390, height: 900 });
    const a = await cards.nth(0).boundingBox();
    const b = await cards.nth(1).boundingBox();
    expect(a && b, "cards need layout boxes").toBeTruthy();
    if (!a || !b) return;
    expect(
      a.y + a.height <= b.y + 4,
      "on mobile, step 2 should sit below step 1 (single column)",
    ).toBe(true);

    await page.setViewportSize({ width: 1280, height: 900 });
    const w0 = await cards.nth(0).boundingBox();
    const w1 = await cards.nth(1).boundingBox();
    expect(w0 && w1).toBeTruthy();
    if (!w0 || !w1) return;
    expect(Math.abs(w0.y - w1.y), "on desktop, first two steps share a row").toBeLessThan(12);
    expect(w1.x, "second card is to the right of the first").toBeGreaterThan(w0.x + w0.width * 0.5);
  });
});
