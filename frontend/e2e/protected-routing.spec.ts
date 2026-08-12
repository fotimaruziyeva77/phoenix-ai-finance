import { expect, test } from "@playwright/test";

import { clearAuthSession, seedAuthSession } from "./helpers/auth-storage";

/**
 * Integration smoke: AuthGate + GuestGate + real storage hydration (no fake auth layer).
 */
test.describe("protected dashboard routing", () => {
  test("anonymous user cannot open /dashboard (redirects to login with next)", async ({ page }) => {
    await clearAuthSession(page);
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?next=/, { timeout: 15_000 });
    await expect(page).toHaveURL(/next=%2Fdashboard/);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Workspace" })).not.toBeVisible();
    await expect(page.getByRole("heading", { name: "Overview" })).not.toBeVisible();
  });

  test("anonymous user cannot open nested dashboard route (next preserves path)", async ({ page }) => {
    await clearAuthSession(page);
    await page.goto("/dashboard/settings");
    await expect(page).toHaveURL(/\/login\?next=/, { timeout: 15_000 });
    await expect(page).toHaveURL(/next=%2Fdashboard%2Fsettings/);
    await expect(page.getByRole("complementary", { name: "Workspace" })).not.toBeVisible();
  });

  test("authenticated user can open dashboard and nested routes", async ({ page }) => {
    await seedAuthSession(page, { userOverrides: { email: "routing@test.com" } });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("complementary", { name: "Workspace" })).toBeVisible();
    await expect(page.getByText("routing@test.com")).toBeVisible();

    await page.goto("/dashboard/leads");
    await expect(page.getByTestId("leads-page-root").getByRole("heading", { name: "Leads", level: 1 })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("authenticated user is redirected away from /login (no guest form after transition)", async ({
    page,
  }) => {
    await seedAuthSession(page);
    await page.goto("/login");
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).not.toBeVisible();
  });

  test("authenticated user is redirected away from /signup", async ({ page }) => {
    await seedAuthSession(page);
    await page.goto("/signup");
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Create your account" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Create account" })).not.toBeVisible();
  });

  test("route transitions: anonymous dashboard shows session loading then login (no shell leak)", async ({
    page,
  }) => {
    await clearAuthSession(page);
    const navigated = page.waitForURL(/\/login\?next=/, { timeout: 15_000 });
    await page.goto("/dashboard");
    /* Gate shows checking copy until redirect — should not expose workspace chrome. */
    await expect(page.getByRole("complementary", { name: "Workspace" })).not.toBeVisible();
    await navigated;
    await expect(page.getByRole("complementary", { name: "Workspace" })).not.toBeVisible();
  });
});
