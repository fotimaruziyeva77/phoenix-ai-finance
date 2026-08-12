import { expect, test } from "@playwright/test";

test.describe("navbar responsive", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("mobile menu opens and auth links navigate correctly", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeHidden();

    await page.getByRole("button", { name: "Open menu" }).click();

    const mobileNav = page.getByRole("navigation", { name: "Mobile menu" });
    await expect(mobileNav).toBeVisible();
    await mobileNav.getByRole("link", { name: "Log in" }).click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });

    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    await page.getByRole("navigation", { name: "Mobile menu" }).getByRole("link", { name: "Get Started" }).click();
    await expect(page).toHaveURL(/\/signup$/, { timeout: 15_000 });
  });

  test("mobile menu section anchors are present", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    const nav = page.getByRole("navigation", { name: "Mobile menu" });
    await expect(nav.getByRole("link", { name: "Features" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Pricing" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "FAQ" })).toBeVisible();
  });
});
