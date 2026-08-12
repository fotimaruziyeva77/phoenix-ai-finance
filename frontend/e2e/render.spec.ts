import { expect, test } from "@playwright/test";

test.describe("basic render", () => {
  test("home page renders main heading and shell", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { level: 1, name: "AI that brings you real clients" }),
    ).toBeVisible();
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("link", { name: "BotForge AI" })).toBeVisible();
  });

  test("login page renders form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { level: 1, name: "Welcome back" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  test("signup page renders form", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { level: 1, name: "Create your account" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Confirm password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
  });

  test("OAuth provider buttons start OAuth (via API redirect or provider host)", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /Continue with Google/i })).toBeEnabled();
    await page.getByRole("button", { name: /Continue with Google/i }).click();
    await expect(page).toHaveURL(
      /\/api\/v1\/auth\/google\/start|accounts\.google\.com/,
      { timeout: 15_000 },
    );

    await page.goto("/login");
    await page.getByRole("button", { name: /Continue with GitHub/i }).click();
    await expect(page).toHaveURL(
      /\/api\/v1\/auth\/github\/start|github\.com\/login/,
      { timeout: 15_000 },
    );
  });
});
