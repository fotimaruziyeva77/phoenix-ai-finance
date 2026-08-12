import { expect, test } from "@playwright/test";

test.describe("navigation", () => {
  test("header links route between home, login, and signup", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);

    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Log in" }).first().click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();

    await page.getByRole("link", { name: "BotForge AI" }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Get Started" }).first().click();
    await expect(page).toHaveURL(/\/signup$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  });

  test("home inline links open auth routes", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("main").getByRole("link", { name: "Log in" }).click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });

    await page.goto("/");
    await page.getByRole("main").getByRole("link", { name: "Get Started" }).click();
    await expect(page).toHaveURL(/\/signup$/, { timeout: 15_000 });
  });
});
