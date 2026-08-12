import { expect, test } from "@playwright/test";

import { clearAuthSession, seedAuthSession } from "./helpers/auth-storage";

/** Must match handler branches below (single source for assertions). */
const OVERVIEW_STUB = {
  users: 7,
  usersActive: 5,
  bots: 3,
  botsSuspended: 1,
} as const;

test.describe("superadmin UI routing", () => {
  test("anonymous user cannot open /superadmin (AuthGate → login with next)", async ({ page }) => {
    await clearAuthSession(page);
    await page.goto("/superadmin");
    await expect(page).toHaveURL(/\/login\?next=/, { timeout: 20_000 });
    await expect(page).toHaveURL(/next=%2Fsuperadmin/);
    await expect(page.getByRole("complementary", { name: "Platform admin" })).not.toBeVisible();
  });

  test("customer_admin is redirected away from /superadmin to dashboard", async ({ page }) => {
    await seedAuthSession(page);
    await page.goto("/superadmin");
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 20_000 });
    await expect(page.getByRole("complementary", { name: "Workspace" })).toBeVisible();
    await expect(page.getByRole("complementary", { name: "Platform admin" })).not.toBeVisible();
  });

  test("superadmin sees platform shell and overview totals from API", async ({ page }) => {
    await seedAuthSession(page, { userOverrides: { role: "superadmin" } });

    await page.route("**/api/v1/admin/**", async (route) => {
      const req = route.request();
      if (req.method() !== "GET") {
        await route.fulfill({ status: 405, body: "not stubbed" });
        return;
      }
      const url = req.url();
      if (url.includes("/admin/users")) {
        const total = url.includes("is_active=true") ? OVERVIEW_STUB.usersActive : OVERVIEW_STUB.users;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total, limit: 1, offset: 0 }),
        });
        return;
      }
      if (url.includes("/admin/bots")) {
        const total = url.includes("platform_suspended=true")
          ? OVERVIEW_STUB.botsSuspended
          : OVERVIEW_STUB.bots;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total, limit: 1, offset: 0 }),
        });
        return;
      }
      await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
    });

    await page.goto("/superadmin");
    await expect(page.getByRole("complementary", { name: "Platform admin" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByTestId("superadmin-overview-total-users")).toHaveText(String(OVERVIEW_STUB.users));
    await expect(page.getByTestId("superadmin-overview-active-users")).toHaveText(
      String(OVERVIEW_STUB.usersActive),
    );
    await expect(page.getByTestId("superadmin-overview-total-bots")).toHaveText(String(OVERVIEW_STUB.bots));
    await expect(page.getByTestId("superadmin-overview-suspended-bots")).toHaveText(
      String(OVERVIEW_STUB.botsSuspended),
    );
  });

  test("superadmin users list shows email returned by API", async ({ page }) => {
    const row = {
      id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
      email: "e2e-list-user@fixture.test",
      full_name: null,
      role: "customer_admin",
      is_active: true,
      is_verified: true,
      suspended_at: null,
      has_password: true,
      oauth_provider_count: 0,
      bot_count: 0,
      created_at: "2026-01-01T00:00:00.000Z",
      updated_at: "2026-01-01T00:00:00.000Z",
    };

    await seedAuthSession(page, { userOverrides: { role: "superadmin" } });

    await page.route("**/api/v1/admin/**", async (route) => {
      const req = route.request();
      if (req.method() !== "GET") {
        await route.fulfill({ status: 405, body: "not stubbed" });
        return;
      }
      const url = req.url();
      if (url.includes("/admin/users?") && url.includes("limit=25")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [row], total: 1, limit: 25, offset: 0 }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, limit: 1, offset: 0 }),
      });
    });

    await page.goto("/superadmin/users");
    await expect(page.getByTestId("superadmin-users-table")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("link", { name: row.email })).toBeVisible();
  });

  test("superadmin bots list shows bot name returned by API", async ({ page }) => {
    const bot = {
      id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
      owner_id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
      owner_email: "owner@fixture.test",
      name: "E2E Stub Bot",
      niche_id: "retail",
      goal_type: "sales",
      status: "active",
      provider_name: "gemini",
      model_name: null,
      widget_configured: false,
      telegram_connected: false,
      platform_suspended_at: null,
      created_at: "2026-01-01T00:00:00.000Z",
      updated_at: "2026-01-01T00:00:00.000Z",
    };

    await seedAuthSession(page, { userOverrides: { role: "superadmin" } });

    await page.route("**/api/v1/admin/**", async (route) => {
      const req = route.request();
      if (req.method() !== "GET") {
        await route.fulfill({ status: 405, body: "not stubbed" });
        return;
      }
      const url = req.url();
      if (url.includes("/admin/bots?") && url.includes("limit=25")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [bot], total: 1, limit: 25, offset: 0 }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0, limit: 1, offset: 0 }),
      });
    });

    await page.goto("/superadmin/bots");
    await expect(page.getByTestId("superadmin-bots-table")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole("link", { name: bot.name })).toBeVisible();
  });
});
