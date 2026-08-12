import { expect, test } from "@playwright/test";

const AUTH_KEY = "botforge_auth_session_v1";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

type AuthSession = {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    full_name: string | null;
    role: string;
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
    updated_at: string;
  };
};

let sharedSessionForStateTests: AuthSession | null = null;

async function registerViaApi(request: import("@playwright/test").APIRequestContext, prefix: string): Promise<AuthSession> {
  let lastStatus = 0;
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const email = `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
    const res = await request.post(`${API_BASE}/api/v1/auth/register`, {
      data: {
        email,
        password: "password123",
        full_name: "Bots Real E2E",
      },
    });
    lastStatus = res.status();
    if (lastStatus === 201) {
      return (await res.json()) as AuthSession;
    }
    if (lastStatus !== 429) {
      expect(lastStatus).toBe(201);
    }
    await new Promise((resolve) => setTimeout(resolve, 2000 + attempt * 250));
  }
  expect(lastStatus).toBe(201);
  throw new Error("registerViaApi exhausted retries");
}

async function getSharedSessionForStateTests(request: import("@playwright/test").APIRequestContext): Promise<AuthSession> {
  if (sharedSessionForStateTests) return sharedSessionForStateTests;
  sharedSessionForStateTests = await registerViaApi(request, "bots-state-shared");
  return sharedSessionForStateTests;
}

async function createBotViaApi(
  request: import("@playwright/test").APIRequestContext,
  accessToken: string,
  body: { name: string; niche_id: string; goal_type: string; status?: string },
) {
  const res = await request.post(`${API_BASE}/api/v1/bots`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    data: body,
  });
  expect(res.status()).toBe(201);
}

async function seedSessionInBrowser(page: import("@playwright/test").Page, session: AuthSession) {
  await page.goto("/");
  await page.evaluate(
    ([key, value]) => window.localStorage.setItem(key, value),
    [
      AUTH_KEY,
      JSON.stringify({
        accessToken: session.access_token,
        refreshToken: session.refresh_token,
        user: session.user,
      }),
    ] as const,
  );
}

async function proxyBotsGetToRealBackend(
  page: import("@playwright/test").Page,
  request: import("@playwright/test").APIRequestContext,
  delayMs = 0,
) {
  await page.route("**/api/v1/bots", async (route) => {
    const req = route.request();
    if (req.method() !== "GET") {
      await route.continue();
      return;
    }
    if (delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    const backendRes = await request.fetch(`${API_BASE}/api/v1/bots`, {
      method: "GET",
      headers: req.headers(),
    });
    const body = await backendRes.text();
    await route.fulfill({
      status: backendRes.status(),
      headers: {
        "content-type": backendRes.headers()["content-type"] ?? "application/json",
      },
      body,
    });
  });
}

test.describe("dashboard bots real backend integration", () => {
  test.skip(!API_BASE, "NEXT_PUBLIC_API_BASE_URL is required for real backend integration.");
  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("bots load from API, values render correctly, and only current user's bots appear", async ({
    page,
    request,
  }) => {
    const owner = await registerViaApi(request, "bots-owner");
    const other = await registerViaApi(request, "bots-other");

    await createBotViaApi(request, owner.access_token, {
      name: "Owner Support Bot",
      niche_id: "education",
      goal_type: "support",
      status: "active",
    });
    await createBotViaApi(request, other.access_token, {
      name: "Other User Bot",
      niche_id: "services",
      goal_type: "sales",
      status: "active",
    });

    await seedSessionInBrowser(page, owner);
    await proxyBotsGetToRealBackend(page, request);
    await page.goto("/dashboard/bots");

    await expect(page.getByTestId("bots-header-create")).toBeVisible();
    await expect(page.getByTestId("bots-list")).toBeVisible();
    await expect(page.getByText("Owner Support Bot").first()).toBeVisible();
    await expect(page.getByText("Other User Bot")).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "Niche" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Goal" })).toBeVisible();
    await expect(page.getByText("Education").first()).toBeVisible();
    await expect(page.getByText("Support").first()).toBeVisible();
    // Service enforces safe default status = draft on create.
    await expect(page.getByTestId("bot-status-draft").first()).toBeVisible();
  });

  test("empty state works with real backend when user has no bots", async ({ page, request }) => {
    const user = await getSharedSessionForStateTests(request);
    await seedSessionInBrowser(page, user);
    await proxyBotsGetToRealBackend(page, request);
    await page.goto("/dashboard/bots");

    await expect(page.getByTestId("bots-header-create")).toBeVisible();
    await expect(page.getByTestId("bots-empty-state")).toBeVisible();
    await expect(page.getByText("No bots in this workspace yet")).toBeVisible();
    await expect(page.getByTestId("bots-list")).toHaveCount(0);
  });

  test("loading state works while API request is in-flight", async ({ page, request }) => {
    const user = await getSharedSessionForStateTests(request);
    await createBotViaApi(request, user.access_token, {
      name: "Loading Bot",
      niche_id: "services",
      goal_type: "faq",
    });
    await seedSessionInBrowser(page, user);
    await proxyBotsGetToRealBackend(page, request, 700);

    await page.goto("/dashboard/bots");
    await expect(page.getByTestId("bots-list-skeleton")).toBeVisible();
    await expect(page.getByText("Loading Bot").first()).toBeVisible();
  });

  test("error state works on API failure and Create Bot CTA stays visible", async ({ page, request }) => {
    const user = await getSharedSessionForStateTests(request);
    await seedSessionInBrowser(page, user);
    await page.route("**/api/v1/bots", async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "internal_error", message: "Internal error" } }),
      });
    });

    await page.goto("/dashboard/bots");
    await expect(page.getByTestId("bots-header-create")).toBeVisible();
    await expect(page.getByTestId("bots-error-banner")).toBeVisible();
    await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  });
});
