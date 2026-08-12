import { expect, test } from "@playwright/test";

const AUTH_KEY = "botforge_auth_session_v1";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

test.describe("create bot wizard real backend flow", () => {
  test.skip(!API_BASE, "NEXT_PUBLIC_API_BASE_URL is required for real backend flow.");

  test("authenticated user completes wizard and created bot appears in list", async ({ page, request }) => {
    const email = `real-flow-${Date.now()}@example.com`;
    const register = await request.post(`${API_BASE}/api/v1/auth/register`, {
      data: {
        email,
        password: "password123",
        full_name: "Real Flow",
      },
    });
    expect(register.status()).toBe(201);
    const session = await register.json();
    const accessToken = String(session.access_token);
    const refreshToken = String(session.refresh_token);
    const user = session.user;

    await page.goto("/");
    await page.evaluate(
      ([key, value]) => window.localStorage.setItem(key, value),
      [
        AUTH_KEY,
        JSON.stringify({
          accessToken,
          refreshToken,
          user,
        }),
      ] as const,
    );

    await page.goto("/dashboard/bots/new");
    await expect(page.getByTestId("create-bot-wizard")).toBeVisible();

    // Proxy bots API to real backend while keeping browser same-origin flow.
    await page.route("**/api/v1/bots", async (route) => {
      const req = route.request();
      if (req.method() !== "POST" && req.method() !== "GET") {
        await route.continue();
        return;
      }
      const query = new URL(req.url()).search;
      const backendResponse = await request.fetch(`${API_BASE}/api/v1/bots`, {
        method: req.method(),
        headers: req.headers(),
        data: req.postData() ?? undefined,
        params: query ? Object.fromEntries(new URLSearchParams(query)) : undefined,
      });
      const body = await backendResponse.text();
      await route.fulfill({
        status: backendResponse.status(),
        headers: {
          "content-type": backendResponse.headers()["content-type"] ?? "application/json",
        },
        body,
      });
    });

    const botName = `Real Bot ${Date.now()}`;
    await page.getByText("Education").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByText("Support").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByLabel("Bot name").fill(botName);
    await page.getByLabel("Short description (optional)").fill("Real sprint 5 flow");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-channel")).toBeVisible();
    await page.getByText("Website widget").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-review")).toBeVisible();
    await page.getByTestId("wizard-nav-finish").click();

    await expect(page).toHaveURL(/\/dashboard\/bots\?created=/);
    await expect(page.getByRole("heading", { name: "Bots", level: 1 })).toBeVisible();
    await expect(page.getByText(botName).first()).toBeVisible();
  });

  test("invalid payload returns clean validation error from backend", async ({ request }) => {
    const email = `real-flow-invalid-${Date.now()}@example.com`;
    const register = await request.post(`${API_BASE}/api/v1/auth/register`, {
      data: {
        email,
        password: "password123",
        full_name: "Real Flow Invalid",
      },
    });
    expect(register.status()).toBe(201);
    const session = await register.json();
    const accessToken = String(session.access_token);

    const invalid = await request.post(`${API_BASE}/api/v1/bots`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      data: {
        name: "Bad Bot",
        niche_id: "invalid_niche",
        goal_type: "support",
      },
    });
    expect(invalid.status()).toBe(422);
    const body = await invalid.json();
    expect(body.error?.code).toBe("bot_validation_error");
    expect(body.error?.message).toBeTruthy();
  });
});
