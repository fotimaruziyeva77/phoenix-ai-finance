import { expect, test } from "@playwright/test";

import {
  apiOriginFromPlaywrightBase,
  clearBrowserWorkspaceState,
  loadSeedOutput,
  loginWithEmailPassword,
} from "./helpers";

const seed = loadSeedOutput();
const describeSeeded = seed ? test.describe : test.describe.skip;

const telegramToken = (process.env.E2E_TELEGRAM_BOT_TOKEN ?? "").trim();

describeSeeded("Real stack — seeded workspace & dashboard artifacts", () => {
  test.describe.configure({ mode: "serial" });

  test("login and verify bots, leads, widget bootstrap, optional Telegram validate", async ({
    page,
    request,
    baseURL,
  }) => {
    test.skip(!baseURL, "Playwright baseURL missing");

    await clearBrowserWorkspaceState(page);
    await loginWithEmailPassword(page, seed!.email, seed!.password);

    await page.goto("/dashboard/bots");
    await expect(page.getByRole("link", { name: seed!.support_bot_name })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: seed!.sales_bot_name })).toBeVisible();

    await page.goto("/dashboard/leads");
    await expect(page.getByTestId("leads-page-root")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: seed!.lead_name })).toBeVisible();

    const origin = apiOriginFromPlaywrightBase(baseURL!);
    const boot = await request.get(`${origin}/api/v1/public/widget/${seed!.widget_public_key}/bootstrap`, {
      headers: { Origin: origin },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();

    if (telegramToken.length >= 10) {
      const loginRes = await request.post(`${origin}/api/v1/auth/login`, {
        data: { email: seed!.email, password: seed!.password },
      });
      expect(loginRes.ok(), await loginRes.text()).toBeTruthy();
      const session = (await loginRes.json()) as { access_token: string };
      const validate = await request.post(
        `${origin}/api/v1/bots/${seed!.support_bot_id}/telegram/token/validate`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          data: { bot_token: telegramToken },
        },
      );
      expect(
        validate.ok() || validate.status() === 409,
        await validate.text(),
      ).toBeTruthy();
    }
  });
});
