import * as path from "node:path";

import { expect, test } from "@playwright/test";

import { clearBrowserWorkspaceState, loginWithEmailPassword, apiOriginFromPlaywrightBase } from "./helpers";

const withObjectStorage = process.env.E2E_WITH_OBJECT_STORAGE === "1";
/** Backend must have a working AI provider (e.g. GEMINI_API_KEY on uvicorn). */
const runWidgetChat = process.env.E2E_WIDGET_CHAT === "1";

test.describe("Real stack — signup, create bot, knowledge, widget (no API mocks)", () => {
  test.describe.configure({ mode: "serial" });

  const unique = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const email = `e2e-onb-${unique}@example.com`;
  const password = "password123";
  const botDisplayName = `E2E Wizard Bot ${unique}`;

  test("registers, completes wizard, optional PDF + widget checks", async ({ page, request, baseURL }) => {
    test.skip(!baseURL, "Playwright baseURL missing");

    await clearBrowserWorkspaceState(page);

    await page.goto("/signup");
    await page.locator("#signup-name").fill("E2E Onboarding");
    await page.locator("#signup-email").fill(email);
    await page.locator("#signup-password").fill(password);
    await page.locator("#signup-confirm").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await page.waitForURL(/\/dashboard/, { timeout: 60_000 });
    await expect(page.getByRole("heading", { level: 2, name: /Hi, E2E/ })).toBeVisible();
    await expect(page.getByText("This is your workspace hub.", { exact: false })).toBeVisible();

    await page.goto("/dashboard/bots/new");
    await expect(page.getByTestId("create-bot-wizard")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("niche-card-education").click();
    await page.getByTestId("wizard-nav-next").click();

    await page.getByTestId("goal-card-support").click();
    await page.getByTestId("wizard-nav-next").click();

    await page.locator("#bot-display-name").fill(botDisplayName);
    await page.getByTestId("wizard-nav-next").click();

    await page.getByTestId("wizard-nav-skip").click();
    await page.getByTestId("wizard-nav-skip").click();

    await page.getByTestId("wizard-nav-finish").click();
    await expect(page.getByTestId("wizard-submitting-success")).toBeVisible({ timeout: 60_000 });

    await page.goto("/dashboard/bots");
    await expect(page.getByRole("link", { name: botDisplayName })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("link", { name: botDisplayName }).click();
    await expect(page.getByTestId("bot-detail-page")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("bot-detail-tab-knowledge").click();
    await expect(page.getByTestId("bot-knowledge-panel")).toBeVisible();

    if (withObjectStorage) {
      const fixture = path.join(__dirname, "fixtures", "minimal.pdf");
      await page.getByLabel("Upload PDF knowledge file").setInputFiles(fixture);
      await expect(page.getByText(/minimal\.pdf/i)).toBeVisible({ timeout: 120_000 });
    }

    await page.getByTestId("bot-detail-tab-widget").click();
    await expect(page.getByTestId("bot-widget-public-key")).toBeVisible({ timeout: 30_000 });
    const widgetKey = (await page.getByTestId("bot-widget-public-key").textContent())?.trim() ?? "";
    expect(widgetKey.length).toBeGreaterThan(8);

    const origin = apiOriginFromPlaywrightBase(baseURL!);
    const boot = await request.get(`${origin}/api/v1/public/widget/${widgetKey}/bootstrap`, {
      headers: { Origin: origin },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();
    const bootJson = (await boot.json()) as { bot_display_name?: string };
    expect(bootJson.bot_display_name).toBeTruthy();

    if (runWidgetChat) {
      const chat = await request.post(`${origin}/api/v1/public/widget/${widgetKey}/chat`, {
        headers: {
          Origin: origin,
          "Content-Type": "application/json",
        },
        data: { message: "Hello from E2E real-stack test." },
      });
      expect(chat.ok(), await chat.text()).toBeTruthy();
      const chatJson = (await chat.json()) as { assistant_text?: string };
      expect((chatJson.assistant_text ?? "").length).toBeGreaterThan(0);
    }
  });

  test("login with created user reaches bots list", async ({ page }) => {
    await clearBrowserWorkspaceState(page);
    await loginWithEmailPassword(page, email, password);
    await page.goto("/dashboard/bots");
    await expect(page.getByRole("link", { name: botDisplayName })).toBeVisible({ timeout: 30_000 });
  });
});
