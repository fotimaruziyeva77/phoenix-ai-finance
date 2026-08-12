import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

const BOTS_E2E_EMAIL = "bots-e2e@example.com";

async function seedBotsSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: {
      email: BOTS_E2E_EMAIL,
      full_name: "Bots E2E",
    },
    accessToken: "bots-test-token",
    refreshToken: "bots-test-refresh",
  });
}

async function mockBotsListEmpty(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/bots", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });
}

async function mockBotsListOne(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/bots", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "550e8400-e29b-41d4-a716-446655440000",
            name: "E2E Bot",
            niche: "Support",
            niche_id: "education",
            goal_type: "support",
            status: "active",
            updated_at: "2026-03-01T12:00:00.000Z",
          },
        ],
      }),
    });
  });
}

test.describe("dashboard bots page (authenticated)", () => {
  test.beforeEach(async ({ page }) => {
    await seedBotsSession(page);
    await mockBotsListEmpty(page);
  });

  test("renders page title, Create Bot, search placeholder, and strong empty state", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard/bots");

    await expect(page.getByRole("heading", { name: "Bots", level: 1 })).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByRole("heading", { name: "Your bots", level: 2 })).toBeVisible();
    await expect(page.getByTestId("bots-page-root")).toBeVisible();
    await expect(page.getByTestId("bots-data-region")).toBeVisible();

    await expect(page.getByTestId("bots-header-create")).toBeVisible();
    await expect(page.getByTestId("bots-header-create")).toHaveText("Create Bot");

    await expect(page.getByTestId("bots-empty-create")).toBeVisible();
    await expect(page.getByTestId("bots-empty-create")).toHaveText("Create your first bot");

    await expect(page.getByTestId("bots-search-placeholder")).toBeVisible();
    await expect(page.getByTestId("bots-filter-placeholder")).toBeVisible();

    await expect(page.getByTestId("bots-empty-state")).toBeVisible();
    await expect(page.getByText("No bots in this workspace yet")).toBeVisible();

    await expect(page.getByTestId("bots-list")).toHaveCount(0);
  });

  test("with API data, shows list structure (columns) and no empty state", async ({ page }) => {
    await mockBotsListOne(page);
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard/bots");

    await expect(page.getByRole("heading", { name: "Bots", level: 1 })).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByTestId("bots-list")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Name" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Niche" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Goal" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Status" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Last updated" })).toBeVisible();
    await expect(page.getByTestId("bots-list-row").getByText("E2E Bot")).toBeVisible();

    await expect(page.getByTestId("bots-empty-state")).toHaveCount(0);
  });

  test("Create Bot in header navigates to new bot placeholder route", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/dashboard/bots");
    await page.getByTestId("bots-header-create").click();
    await expect(page).toHaveURL(/\/dashboard\/bots\/new$/);
    await expect(page.getByTestId("create-bot-wizard")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Create a bot", level: 1 })).toBeVisible();
    await expect(page.getByTestId("wizard-stepper")).toBeVisible();
  });
});
