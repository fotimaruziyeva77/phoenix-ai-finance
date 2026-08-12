import { expect, test } from "@playwright/test";

test.describe("footer", () => {
  test("footer is visible with brand and copyright", async ({ page }) => {
    await page.goto("/");
    const footer = page.getByRole("contentinfo");
    await expect(footer).toBeVisible();
    await expect(footer.getByText("Build and ship AI workflows in one place.")).toBeVisible();
    await expect(footer.getByText(/All rights reserved/)).toBeVisible();
    await expect(footer.getByText("support@example.com")).toBeVisible();
  });

  test("footer links navigate correctly", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("contentinfo").getByRole("link", { name: "Terms" }).click();
    await expect(page).toHaveURL(/\/terms$/);
    await expect(page.getByRole("heading", { name: /Terms of service/i })).toBeVisible();

    await page.goto("/");
    await page.getByRole("contentinfo").getByRole("link", { name: "Privacy" }).click();
    await expect(page).toHaveURL(/\/privacy$/);
    await expect(page.getByRole("heading", { name: /Privacy policy/i })).toBeVisible();

    await page.goto("/");
    await page.getByRole("contentinfo").getByRole("link", { name: "Features" }).click();
    await expect(page).toHaveURL(/#features$/);

    await page.goto("/");
    await page.getByRole("contentinfo").getByRole("link", { name: "Pricing" }).click();
    await expect(page).toHaveURL(/#pricing$/);

    await page.goto("/");
    await page.getByRole("contentinfo").getByRole("link", { name: "FAQ" }).click();
    /* Next.js ``Link`` to ``/#faq`` from ``/`` may not append the hash to ``location``; assert the section instead. */
    await expect(page.locator("#faq")).toBeVisible();
    await expect(page.locator("#faq")).toBeInViewport();
  });
});
