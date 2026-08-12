import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

const LAYOUT_E2E_EMAIL = "layout-e2e@example.com";

async function seedDashboardSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: {
      email: LAYOUT_E2E_EMAIL,
      full_name: "Layout E2E",
    },
    accessToken: "layout-test-token",
    refreshToken: "layout-test-refresh",
  });
}

test.describe("dashboard layout (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await seedDashboardSession(page);
  });

  test("authenticated shell renders: sidebar, topbar, main", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByRole("complementary", { name: "Workspace" })).toBeVisible();
    await expect(page.getByTestId("dashboard-nav-desktop")).toBeVisible();
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByText(LAYOUT_E2E_EMAIL)).toBeVisible();
  });

  test("sidebar lists all section links and marketing escape link", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");

    const primary = page.getByTestId("dashboard-nav-desktop");
    for (const label of [
      "Overview",
      "Bots",
      "Leads",
      "Knowledge",
      "Channels",
      "Analytics",
      "Settings",
    ] as const) {
      await expect(primary.getByRole("link", { name: label })).toBeVisible({ timeout: 15_000 });
    }
    await expect(page.getByRole("link", { name: "Marketing site" })).toBeVisible();
  });

  test("primary nav routes update URL and topbar title", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");

    await page.getByTestId("dashboard-nav-desktop").getByRole("link", { name: "Bots" }).click();
    await expect(page).toHaveURL(/\/dashboard\/bots$/);
    await expect(page.getByRole("heading", { name: "Bots", level: 1 })).toBeVisible();

    await page.getByTestId("dashboard-nav-desktop").getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL(/\/dashboard\/settings$/);
    await expect(page.getByRole("heading", { name: "Settings", level: 1 })).toBeVisible();
  });

  test("desktop: no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({ timeout: 15_000 });

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  });

  test("mobile: menu opens drawer, nav works, no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({ timeout: 15_000 });

    /* Topbar menu control only (backdrop is a separate control). */
    const menuToggle = page.getByRole("banner").getByRole("button", { name: /Open navigation|Close navigation/ });
    await expect(menuToggle).toBeVisible();
    await menuToggle.click();
    await expect(menuToggle).toHaveAttribute("aria-expanded", "true");

    const drawer = page.locator("#dashboard-nav-drawer");
    await expect(drawer).toBeVisible();

    await drawer.getByTestId("dashboard-nav-mobile").getByRole("link", { name: "Leads" }).click();
    await expect(page).toHaveURL(/\/dashboard\/leads$/);
    await expect(page.getByTestId("leads-page-root").getByRole("heading", { name: "Leads", level: 1 })).toBeVisible();

    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  });
});
