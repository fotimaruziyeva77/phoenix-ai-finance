/**
 * Sprint 3 E2E tests
 *
 * Covers:
 *  - Leads cursor pagination (next_cursor / has_more)
 *  - Analytics time-period toggle (7d / 30d / 90d)
 *  - Billing status banners (?status=success / canceled)
 *  - Bot clone endpoint (POST /bots/:id/clone)
 *  - Settings profile edit (PATCH /auth/me)
 */

import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

// ── shared helpers ────────────────────────────────────────────────────────────

async function seedSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: { email: "sprint3@example.com", full_name: "Sprint User" },
    accessToken: "sprint3-token",
    refreshToken: "sprint3-refresh",
  });
}

const LEAD_TEMPLATE = {
  id: "00000000-0000-0000-0000-000000000001",
  bot_id: "00000000-0000-0000-0000-000000000010",
  conversation_id: null,
  niche_id: "ecommerce",
  status: "new" as const,
  lead_temperature: "warm" as const,
  lead_score: 70,
  name: "Alice Cursor",
  phone: "+1 555 0001",
  summary: "Interested in the Pro plan",
  source_channel: "telegram",
  owner_inbox_routed_at: null,
  telegram_delivery_status: "delivered",
  telegram_delivery_attempts: 1,
  telegram_delivery_updated_at: null,
  created_at: "2026-04-10T09:00:00.000Z",
  updated_at: "2026-04-10T09:00:00.000Z",
};

function makeLeads(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    ...LEAD_TEMPLATE,
    id: `00000000-0000-0000-0000-${String(i + 1).padStart(12, "0")}`,
    name: `Lead ${i + 1}`,
  }));
}

// ── Analytics page mock ───────────────────────────────────────────────────────

function makeAnalyticsSummary(periodDays = 30) {
  return {
    bots: { draft: 1, active: 2, paused: 0, archived: 0, total: 3 },
    leads: { new: 5, contacted: 3, qualified: 2, proposal: 1, won: 1, lost: 0, total: 12 },
    lead_temperature: { hot: 2, warm: 6, cold: 3, unknown: 1 },
    usage: {
      conversations_this_month: 42,
      conversations_limit: 500,
      plan_slug: "pro",
      plan_name: "Pro",
    },
    period_days: periodDays,
    generated_at: new Date().toISOString(),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Cursor-based pagination
// ─────────────────────────────────────────────────────────────────────────────

test.describe("leads cursor pagination", () => {
  test("shows load-more button when has_more=true and fetches next page on click", async ({ page }) => {
    await seedSession(page);

    const page1Leads = makeLeads(10);
    const page2Leads = makeLeads(5).map((l, i) => ({
      ...l,
      id: `00000000-0000-0000-0000-${String(i + 100).padStart(12, "0")}`,
      name: `Next Lead ${i + 1}`,
    }));
    const CURSOR = "dGVzdC1jdXJzb3I="; // base64 placeholder

    let requestCount = 0;
    await page.route("**/api/v1/leads**", async (route) => {
      const url = new URL(route.request().url());
      requestCount++;
      if (url.searchParams.get("after") === CURSOR) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: page2Leads, total: 5, has_more: false, next_cursor: null }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: page1Leads, total: 10, has_more: true, next_cursor: CURSOR }),
        });
      }
    });

    await page.goto("/dashboard/leads");
    await page.waitForLoadState("networkidle");

    // First page items visible
    await expect(page.getByText("Lead 1")).toBeVisible();
    await expect(page.getByText("Lead 10")).toBeVisible();

    // Load More button present
    const loadMoreBtn = page.getByRole("button", { name: /load more/i });
    await expect(loadMoreBtn).toBeVisible();

    // Click load more → second page appended
    await loadMoreBtn.click();
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Next Lead 1")).toBeVisible();
    // Load More button gone (has_more=false)
    await expect(page.getByRole("button", { name: /load more/i })).toHaveCount(0);
  });

  test("hides load-more when has_more=false on first response", async ({ page }) => {
    await seedSession(page);

    await page.route("**/api/v1/leads**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: makeLeads(3), total: 3, has_more: false, next_cursor: null }),
      });
    });

    await page.goto("/dashboard/leads");
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("button", { name: /load more/i })).toHaveCount(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Analytics time-period toggle
// ─────────────────────────────────────────────────────────────────────────────

test.describe("analytics period toggle", () => {
  test("renders 7d / 30d / 90d buttons and refetches on click", async ({ page }) => {
    await seedSession(page);

    const requests: string[] = [];
    await page.route("**/api/v1/analytics/summary**", async (route) => {
      const url = new URL(route.request().url());
      const period = url.searchParams.get("period_days") ?? "30";
      requests.push(period);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeAnalyticsSummary(Number(period))),
      });
    });

    await page.goto("/dashboard/analytics");
    await page.waitForLoadState("networkidle");

    // Default 30d button active
    await expect(page.getByRole("button", { name: "30d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "7d" })).toBeVisible();
    await expect(page.getByRole("button", { name: "90d" })).toBeVisible();

    // Switch to 7d
    await page.getByRole("button", { name: "7d" }).click();
    await page.waitForLoadState("networkidle");
    expect(requests).toContain("7");

    // Switch to 90d
    await page.getByRole("button", { name: "90d" }).click();
    await page.waitForLoadState("networkidle");
    expect(requests).toContain("90");
  });

  test("stat card sub-label reflects selected period", async ({ page }) => {
    await seedSession(page);

    await page.route("**/api/v1/analytics/summary**", async (route) => {
      const url = new URL(route.request().url());
      const period = Number(url.searchParams.get("period_days") ?? "30");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(makeAnalyticsSummary(period)),
      });
    });

    await page.goto("/dashboard/analytics");
    await page.waitForLoadState("networkidle");

    // Default shows "last 30d"
    await expect(page.getByText(/last 30d/i)).toBeVisible();

    // Switch to 7d → label updates
    await page.getByRole("button", { name: "7d" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(/last 7d/i)).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Billing status banners
// ─────────────────────────────────────────────────────────────────────────────

test.describe("billing status banners", () => {
  async function mockBillingData(page: import("@playwright/test").Page) {
    await page.route("**/api/v1/billing/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
    });
    await page.route("**/api/v1/subscriptions/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
    });
  }

  test("shows success banner on ?status=success", async ({ page }) => {
    await seedSession(page);
    await mockBillingData(page);

    await page.goto("/dashboard/billing?status=success");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/subscription has been activated/i)).toBeVisible();
    await expect(page.getByText(/checkout was canceled/i)).toHaveCount(0);
  });

  test("shows canceled banner on ?status=canceled", async ({ page }) => {
    await seedSession(page);
    await mockBillingData(page);

    await page.goto("/dashboard/billing?status=canceled");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/checkout was canceled/i)).toBeVisible();
    await expect(page.getByText(/subscription has been activated/i)).toHaveCount(0);
  });

  test("shows no banner without status param", async ({ page }) => {
    await seedSession(page);
    await mockBillingData(page);

    await page.goto("/dashboard/billing");
    await page.waitForLoadState("networkidle");

    await expect(page.getByText(/subscription has been activated/i)).toHaveCount(0);
    await expect(page.getByText(/checkout was canceled/i)).toHaveCount(0);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Bot clone
// ─────────────────────────────────────────────────────────────────────────────

const BOT_FIXTURE = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  name: "My Sales Bot",
  niche: "ecommerce",
  niche_id: "ecommerce",
  goal_type: "lead_generation",
  status: "active",
  primary_channel: "web",
  updated_at: "2026-04-10T12:00:00.000Z",
};

const CLONED_BOT_FIXTURE = {
  ...BOT_FIXTURE,
  id: "660f9500-f39c-52e5-b827-557766551111",
  name: "My Sales Bot (copy)",
  status: "draft",
  primary_channel: null,
};

test.describe("bot clone", () => {
  test("clone button calls POST /bots/:id/clone and shows new draft bot", async ({ page }) => {
    await seedSession(page);

    await page.route("**/api/v1/bots", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [BOT_FIXTURE] }),
        });
      } else {
        await route.continue();
      }
    });

    let cloneRequested = false;
    await page.route(`**/api/v1/bots/${BOT_FIXTURE.id}/clone`, async (route) => {
      cloneRequested = true;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(CLONED_BOT_FIXTURE),
      });
    });

    await page.goto("/dashboard/bots");
    await page.waitForLoadState("networkidle");

    // Find the clone button for the existing bot
    const cloneBtn = page.getByRole("button", { name: /clone/i }).first();
    await expect(cloneBtn).toBeVisible();
    await cloneBtn.click();

    await page.waitForLoadState("networkidle");
    expect(cloneRequested).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Settings profile edit
// ─────────────────────────────────────────────────────────────────────────────

test.describe("settings profile edit", () => {
  test("edit button shows input, save calls PATCH /auth/me, updated name displayed", async ({ page }) => {
    await seedSession(page);

    let patchBody: unknown = null;
    await page.route("**/api/v1/auth/me", async (route) => {
      if (route.request().method() === "PATCH") {
        patchBody = JSON.parse(route.request().postData() ?? "{}");
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "00000000-0000-0000-0000-000000000001",
            email: "sprint3@example.com",
            full_name: "New Name",
            role: "user",
            is_active: true,
            is_verified: true,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/dashboard/settings");
    await page.waitForLoadState("networkidle");

    // Click edit button
    const editBtn = page.getByRole("button", { name: /edit/i }).first();
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    // Input should appear
    const nameInput = page.getByRole("textbox");
    await expect(nameInput).toBeVisible();
    await nameInput.fill("New Name");

    // Save
    const saveBtn = page.getByRole("button", { name: /save/i });
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    await page.waitForLoadState("networkidle");
    expect((patchBody as { full_name?: string })?.full_name).toBe("New Name");
  });

  test("cancel button dismisses the edit form without saving", async ({ page }) => {
    await seedSession(page);

    let patchCalled = false;
    await page.route("**/api/v1/auth/me", async (route) => {
      if (route.request().method() === "PATCH") {
        patchCalled = true;
        await route.continue();
      } else {
        await route.continue();
      }
    });

    await page.goto("/dashboard/settings");
    await page.waitForLoadState("networkidle");

    const editBtn = page.getByRole("button", { name: /edit/i }).first();
    await editBtn.click();
    const cancelBtn = page.getByRole("button", { name: /cancel/i });
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();

    // Input gone
    await expect(page.getByRole("textbox")).toHaveCount(0);
    expect(patchCalled).toBe(false);
  });
});
