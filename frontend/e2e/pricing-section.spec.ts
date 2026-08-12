import { expect, test } from "@playwright/test";

const PLAN_NAMES = ["Starter", "Pro", "Business"] as const;

test.describe("Pricing section", () => {
  test("three plans are visible with names and pricing lines", async ({ page }) => {
    await page.goto("/#pricing");
    const section = page.locator("#pricing");
    await expect(section.getByRole("heading", { name: "Simple pricing", level: 2 })).toBeVisible();

    const cards = section.locator(":scope > ul > li");
    await expect(cards).toHaveCount(3);

    for (const name of PLAN_NAMES) {
      await expect(section.getByRole("heading", { name, level: 3 })).toBeVisible();
    }

    await expect(section.getByText("Free to explore · paid tiers from —")).toBeVisible();
    await expect(section.getByText("From — / month · scales with usage")).toBeVisible();
    await expect(section.getByText("Custom · invoicing available")).toBeVisible();
  });

  test("Start Free CTAs navigate to signup", async ({ page }) => {
    await page.goto("/");
    const ctas = page.locator("#pricing").getByRole("link", { name: "Start Free" });
    await expect(ctas).toHaveCount(3);

    await ctas.first().click();
    await expect(page).toHaveURL(/\/signup$/);

    await page.goto("/");
    await ctas.nth(1).click();
    await expect(page).toHaveURL(/\/signup$/);

    await page.goto("/");
    await ctas.nth(2).click();
    await expect(page).toHaveURL(/\/signup$/);
  });

  test("layout: stacked on mobile, row on desktop", async ({ page }) => {
    await page.goto("/");
    const cards = page.locator("#pricing > ul > li");

    await page.setViewportSize({ width: 390, height: 900 });
    const m0 = await cards.nth(0).boundingBox();
    const m1 = await cards.nth(1).boundingBox();
    expect(m0 && m1).toBeTruthy();
    if (!m0 || !m1) return;
    expect(m0.y + m0.height <= m1.y + 4, "plans stack vertically on narrow viewports").toBe(true);

    await page.setViewportSize({ width: 1280, height: 900 });
    const d0 = await cards.nth(0).boundingBox();
    const d1 = await cards.nth(1).boundingBox();
    expect(d0 && d1).toBeTruthy();
    if (!d0 || !d1) return;
    expect(Math.abs(d0.y - d1.y), "first two plans share a row on wide viewports").toBeLessThan(12);
    expect(d1.x, "second plan is to the right of the first").toBeGreaterThan(d0.x + d0.width * 0.4);
  });
});
