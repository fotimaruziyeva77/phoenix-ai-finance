import { expect, test, type Page } from "@playwright/test";

import { AUTH_KEY, E2E_MOCK_USER, seedAuthSession } from "./helpers/auth-storage";

/** Form validation uses ``<p role="alert">``; Next.js also exposes ``#__next-route-announcer__`` as role=alert. */
function formAlert(page: Page) {
  return page.locator("p[role='alert']");
}

function authSessionBody(overrides?: { email?: string }) {
  const user = { ...E2E_MOCK_USER, ...overrides };
  return {
    user,
    access_token: "e2e-access-token",
    refresh_token: "e2e-refresh-token",
    token_type: "Bearer" as const,
    expires_in: 900,
  };
}

async function installAuthApiMocks(page: Page) {
  await page.route("**/api/v1/auth/login", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(authSessionBody()),
    });
  });

  await page.route("**/api/v1/auth/register", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    let email = E2E_MOCK_USER.email;
    try {
      const post = route.request().postDataJSON() as { email?: string } | null;
      if (post?.email) email = post.email;
    } catch {
      /* non-JSON body */
    }
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(authSessionBody({ email })),
    });
  });

  await page.route("**/api/v1/auth/logout", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({ status: 204, body: "" });
  });
}

test.describe("auth flow", () => {
  test.beforeEach(async ({ page }) => {
    await installAuthApiMocks(page);
  });

  test("signup page renders", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
  });

  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  test("login validation shows for empty submit", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(formAlert(page)).toContainText("Email and password are required.");
  });

  test("signup validation shows for empty submit", async ({ page }) => {
    await page.goto("/signup");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(formAlert(page)).toContainText(
      "Email and both password fields are required.",
    );
  });

  test("signup validation for short password", async ({ page }) => {
    await page.goto("/signup");
    await page.locator("#signup-email").fill("shortpw@test.com");
    await page.locator("#signup-password").fill("short");
    await page.locator("#signup-confirm").fill("short");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(formAlert(page)).toContainText("at least 8 characters");
  });

  test("successful signup redirects to dashboard", async ({ page }) => {
    const email = `new-${Date.now()}@test.com`;
    await page.goto("/signup");
    await page.locator("#signup-email").fill(email);
    await page.locator("#signup-password").fill("password123");
    await page.locator("#signup-confirm").fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#login-email").fill("e2e@example.com");
    await page.locator("#login-password").fill("password123");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    const stored = await page.evaluate((k) => window.localStorage.getItem(k), AUTH_KEY);
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!) as { accessToken?: string };
    expect(parsed.accessToken).toBe("e2e-access-token");
  });

  test("protected dashboard redirects anonymous users to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?next=/, { timeout: 15_000 });
    await expect(page).toHaveURL(/next=%2Fdashboard/);
  });

  test("authenticated user can open dashboard from stored session", async ({ page }) => {
    await seedAuthSession(page, {
      userOverrides: { email: "stored@test.com" },
      accessToken: "stored-access",
      refreshToken: "stored-refresh",
    });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/stored@test\.com/)).toBeVisible();
  });

  test("authenticated user visiting login is redirected away (guest gate)", async ({ page }) => {
    await seedAuthSession(page, {
      accessToken: "stored-access",
      refreshToken: "stored-refresh",
    });
    await page.goto("/login");
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  });

  test("authenticated user visiting login with next lands on that path", async ({ page }) => {
    await seedAuthSession(page, {
      accessToken: "stored-access",
      refreshToken: "stored-refresh",
    });
    await page.goto("/login?next=%2Fdashboard%2Fsettings");
    await expect(page).toHaveURL(/\/dashboard\/settings$/, { timeout: 15_000 });
  });

  test("logout clears session and returns to login-capable state", async ({ page }) => {
    await seedAuthSession(page, {
      accessToken: "stored-access",
      refreshToken: "stored-refresh",
    });
    await page.goto("/dashboard", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Log out" }).first().click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });

    const cleared = await page.evaluate((k) => window.localStorage.getItem(k), AUTH_KEY);
    expect(cleared).toBeNull();

    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Log in" })).toBeVisible();
  });
});
