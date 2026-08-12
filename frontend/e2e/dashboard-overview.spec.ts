import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

const OVERVIEW_E2E_EMAIL = "overview-e2e@example.com";

async function seedOverviewSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: {
      email: OVERVIEW_E2E_EMAIL,
      full_name: "Overview E2E",
    },
    accessToken: "overview-test-token",
    refreshToken: "overview-test-refresh",
  });
}

test.describe("dashboard overview (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await seedOverviewSession(page);
  });

  test("renders overview shell, welcome, quick actions, and empty-state copy (no simulated metrics)", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");

    await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByRole("heading", { name: "Hi, Overview", level: 2 })).toBeVisible();
    await expect(page.getByText("This is your workspace hub.")).toBeVisible();

    await expect(page.getByTestId("overview-quick-actions")).toBeVisible();
    await expect(page.getByText("Quick actions")).toBeVisible();
    await expect(page.getByTestId("overview-action-bots")).toBeVisible();
    await expect(page.getByTestId("overview-action-knowledge")).toBeVisible();
    await expect(page.getByTestId("overview-action-channels")).toBeVisible();

    await expect(page.getByRole("heading", { name: "Create your first bot", level: 2 })).toBeVisible();
    await expect(
      page.getByText("You do not have any bots in this workspace yet.", { exact: false }),
    ).toBeVisible();

    await expect(page.getByText("Activity (coming soon)")).toBeVisible();
    await expect(page.getByText("Nothing is simulated")).toBeVisible();
    await expect(page.getByText("No leads yet")).toBeVisible();
    await expect(page.getByText("No channels connected")).toBeVisible();
  });

  test("quick action Create Bot navigates to /dashboard/bots", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");
    await page.getByTestId("overview-action-bots").click();
    await expect(page).toHaveURL(/\/dashboard\/bots$/);
  });

  test("quick action Upload Knowledge navigates to /dashboard/knowledge", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");
    await page.getByTestId("overview-action-knowledge").click();
    await expect(page).toHaveURL(/\/dashboard\/knowledge$/, { timeout: 15_000 });
  });

  test("quick action Connect Channel navigates to /dashboard/channels", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard");
    await page.getByTestId("overview-action-channels").click();
    await expect(page).toHaveURL(/\/dashboard\/channels$/, { timeout: 15_000 });
  });
});
