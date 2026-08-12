import { expect, test } from "@playwright/test";

const EXPECTED_TITLES = [
  "Education",
  "Healthcare (clinic)",
  "Dev / Agency",
  "Services",
] as const;

test.describe("Niche section", () => {
  test("four niche cards are visible with titles", async ({ page }) => {
    await page.goto("/#niches");
    const section = page.locator("#niches");
    await expect(section.getByRole("heading", { name: "Built for your niche", level: 2 })).toBeVisible();

    const cards = section.locator("ul > li");
    await expect(cards).toHaveCount(4);

    for (const title of EXPECTED_TITLES) {
      await expect(section.getByRole("heading", { name: title, level: 3 })).toBeVisible();
    }
  });

  test("hover applies lift / shadow on a card", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");
    const card = page.locator("#niches ul > li").first();

    const before = await card.evaluate((el) => ({
      transform: getComputedStyle(el).transform,
      boxShadow: getComputedStyle(el).boxShadow,
    }));

    await card.hover();

    await expect
      .poll(async () => {
        const t = await card.evaluate((el) => getComputedStyle(el).transform);
        return t !== "none";
      })
      .toBe(true);

    const after = await card.evaluate((el) => ({
      transform: getComputedStyle(el).transform,
      boxShadow: getComputedStyle(el).boxShadow,
    }));
    expect(before.transform !== after.transform || before.boxShadow !== after.boxShadow).toBe(true);
  });

  test("mobile: cards stack vertically", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto("/");
    const cards = page.locator("#niches ul > li");
    const a = await cards.nth(0).boundingBox();
    const b = await cards.nth(1).boundingBox();
    expect(a && b).toBeTruthy();
    if (!a || !b) return;
    expect(
      a.y + a.height <= b.y + 4,
      "second card should appear below the first on narrow viewports",
    ).toBe(true);
  });
});
