import { expect, test } from "@playwright/test";

test.describe("hero section", () => {
  test("headline and subtext are visible (readable)", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: /AI that brings you real clients/ })).toBeVisible();
    await expect(
      page.getByText("Create a smart AI bot that talks to visitors", { exact: false }),
    ).toBeVisible();

    const subtextSize = await page.locator("#hero-heading + p").evaluate((el) =>
      parseFloat(getComputedStyle(el).fontSize),
    );
    expect(subtextSize, "subtext font-size should be at least 15px for readability").toBeGreaterThanOrEqual(15);

    const headlineWeight = await page.locator("#hero-heading").evaluate((el) => getComputedStyle(el).fontWeight);
    expect(Number(headlineWeight), "headline should be bold").toBeGreaterThanOrEqual(600);
  });

  test("primary and secondary CTAs are in viewport (above the fold)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/");
    const primary = page.getByRole("link", { name: "Create Your Bot" });
    const secondary = page.getByRole("link", { name: "See How It Works" });
    await expect(primary).toBeInViewport();
    await expect(secondary).toBeInViewport();
  });

  test("CTAs are clickable and navigate correctly", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Create Your Bot" }).click();
    await expect(page).toHaveURL(/\/signup$/);

    await page.goto("/");
    await page.getByRole("link", { name: "See How It Works" }).click();
    await expect(page).toHaveURL(/#how-it-works$/);
    await expect(page.locator("#how-it-works")).toBeInViewport();
  });

  test("mobile: no horizontal overflow, CTAs in viewport, links work", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(
      overflow.scrollWidth,
      "page should not scroll horizontally",
    ).toBeLessThanOrEqual(overflow.clientWidth + 1);

    const primary = page.getByRole("link", { name: "Create Your Bot" });
    const secondary = page.getByRole("link", { name: "See How It Works" });
    await expect(primary).toBeInViewport();
    await expect(secondary).toBeInViewport();

    const primaryBox = await primary.boundingBox();
    const secondaryBox = await secondary.boundingBox();
    expect(primaryBox?.height, "touch-friendly primary CTA height").toBeGreaterThanOrEqual(40);
    expect(secondaryBox?.height, "touch-friendly secondary CTA height").toBeGreaterThanOrEqual(40);

    await primary.click();
    await expect(page).toHaveURL(/\/signup$/);
  });
});
