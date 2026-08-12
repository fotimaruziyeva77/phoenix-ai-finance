import { expect, test } from "@playwright/test";

import { seedAuthSession } from "./helpers/auth-storage";

const WIZARD_E2E_EMAIL = "wizard-e2e@example.com";

async function seedWizardSession(page: import("@playwright/test").Page) {
  await seedAuthSession(page, {
    userOverrides: {
      email: WIZARD_E2E_EMAIL,
      full_name: "Wizard E2E",
    },
    accessToken: "wizard-test-token",
    refreshToken: "wizard-test-refresh",
  });
}

/** Niche → goal → basics (filled) → channel (website widget) → knowledge (enter). */
async function reachKnowledgeStep(page: import("@playwright/test").Page, botName: string) {
  await page.getByText("Education").click();
  await page.getByTestId("wizard-nav-next").click();
  await page.getByText("Support").click();
  await page.getByTestId("wizard-nav-next").click();
  await page.getByLabel("Bot name").fill(botName);
  await page.getByTestId("wizard-nav-next").click();
  await page.getByText("Website widget").click();
  await page.getByTestId("wizard-nav-next").click();
}

async function reachReviewStep(page: import("@playwright/test").Page, botName: string) {
  await reachKnowledgeStep(page, botName);
  await page.getByTestId("wizard-nav-next").click();
}

async function reachReviewWithBothChannel(page: import("@playwright/test").Page, botName: string) {
  await page.getByText("Education").click();
  await page.getByTestId("wizard-nav-next").click();
  await page.getByText("Support").click();
  await page.getByTestId("wizard-nav-next").click();
  await page.getByLabel("Bot name").fill(botName);
  await page.getByTestId("wizard-nav-next").click();
  await page.getByText("Both").click();
  await page.getByTestId("wizard-nav-next").click();
  await page.getByTestId("wizard-nav-next").click();
}

test.describe("create bot wizard", () => {
  test.beforeEach(async ({ page }) => {
    await seedWizardSession(page);
    await page.goto("/dashboard/bots/new");
    await expect(page.getByTestId("niche-card-education")).toBeVisible({ timeout: 30000 });
  });

  test("stepper renders and first step is visible", async ({ page }) => {
    await expect(page.getByTestId("create-bot-wizard")).toBeVisible();
    await expect(page.getByTestId("wizard-stepper")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Create a bot", level: 1 })).toBeVisible();
    await expect(page.getByTestId("wizard-step-niche")).toBeVisible();

    for (const label of ["Niche", "Goal", "Basics", "Channel", "Knowledge", "Review"] as const) {
      await expect(page.getByTestId("wizard-stepper").getByText(label)).toBeVisible();
    }

    await expect(page.getByTestId("niche-grid").locator("label[data-testid^='niche-card-']")).toHaveCount(4);
  });

  test("niche selection is single-select and selected state is clear", async ({ page }) => {
    await expect(page.getByTestId("wizard-step-niche")).toBeVisible();
    const nicheRadios = page.locator('input[type="radio"][name="niche"]');
    await expect(nicheRadios).toHaveCount(4);

    await page.getByText("Education").click();
    await expect(page.locator('input[type="radio"][name="niche"]:checked')).toHaveCount(1);
    await expect(page.getByRole("radio", { name: "Education" })).toBeChecked();
    await expect(page.getByTestId("niche-card-education").locator("[data-selected='true']")).toHaveCount(1);

    await page.getByText("Services").click();
    await expect(page.locator('input[type="radio"][name="niche"]:checked')).toHaveCount(1);
    await expect(page.getByRole("radio", { name: "Services" })).toBeChecked();
    await expect(page.getByTestId("niche-card-services").locator("[data-selected='true']")).toHaveCount(1);
    await expect(page.getByTestId("niche-card-education").locator("[data-selected='true']")).toHaveCount(0);
  });

  test("goal step renders 4 options, enforces single-select, and blocks next when empty", async ({ page }) => {
    await page.getByText("Education").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();

    const goalCards = page.getByTestId("goal-grid").locator("label[data-testid^='goal-card-']");
    await expect(goalCards).toHaveCount(4);
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText("Choose a goal to continue.");
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();

    await page.getByText("Support").click();
    await expect(page.locator('input[type="radio"][name="goal"]:checked')).toHaveCount(1);
    await expect(page.getByRole("radio", { name: "Support" })).toBeChecked();
    await expect(page.getByTestId("goal-card-support").locator("[data-selected='true']")).toHaveCount(1);

    await page.getByText("Consulting").click();
    await expect(page.locator('input[type="radio"][name="goal"]:checked')).toHaveCount(1);
    await expect(page.getByRole("radio", { name: "Consulting" })).toBeChecked();
    await expect(page.getByTestId("goal-card-consulting").locator("[data-selected='true']")).toHaveCount(1);
    await expect(page.getByTestId("goal-card-support").locator("[data-selected='true']")).toHaveCount(0);
  });

  test("next/back and transitions work across required steps", async ({ page }) => {
    await page.getByText("Healthcare / Clinic").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();
    await expect(page.getByTestId("goal-grid").locator("label[data-testid^='goal-card-']")).toHaveCount(4);

    await page.getByText("Support").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-basics")).toBeVisible();

    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();
    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByTestId("wizard-step-niche")).toBeVisible();
  });

  test("state is preserved while navigating between steps", async ({ page }) => {
    await page.getByText("Dev / Agency").click();
    await page.getByTestId("wizard-nav-next").click();

    await page.getByText("Sales").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-basics")).toBeVisible();

    const name = page.getByLabel("Bot name");
    await name.fill("Retention Assistant");
    await page.getByLabel("Language (minimal for now)").selectOption("es");
    await page.getByLabel("Short description (optional)").fill("Helps qualify and route incoming leads.");
    await page.getByText("Professional & formal").click();

    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();
    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByTestId("wizard-step-niche")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-basics")).toBeVisible();
    await expect(page.getByLabel("Bot name")).toHaveValue("Retention Assistant");
    await expect(page.getByLabel("Language (minimal for now)")).toHaveValue("es");
    await expect(page.getByLabel("Short description (optional)")).toHaveValue(
      "Helps qualify and route incoming leads.",
    );
    await expect(page.getByRole("radio", { name: "Professional & formal" })).toBeChecked();
  });

  test("validation blocks progression and clears after valid input", async ({ page }) => {
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText("Choose a niche to continue.");
    await expect(page.getByTestId("wizard-step-niche")).toBeVisible();

    await page.getByText("Services").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-goal")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText("Choose a goal to continue.");

    await page.getByText("FAQ").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-basics")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText(
      "Enter a bot name (at least 2 characters).",
    );
    await page.getByLabel("Bot name").fill("L");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText(
      "Enter a bot name (at least 2 characters).",
    );

    await page.getByLabel("Bot name").fill("Lead Bot");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-channel")).toBeVisible();
    await page.getByText("Website widget").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-knowledge")).toBeVisible();
    await expect(page.getByTestId("wizard-step-error")).toHaveCount(0);
  });

  test("basics step validates required name while optional fields keep flow clean", async ({ page }) => {
    await page.getByText("Education").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByText("Support").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-basics")).toBeVisible();

    await expect(page.getByText("Shown in your workspace and future channel settings.")).toBeVisible();
    await expect(
      page.getByText("Tone is optional. You can leave it blank and adjust personality after launch."),
    ).toBeVisible();
    await expect(page.getByLabel("Language (minimal for now)")).toBeVisible();
    await expect(page.getByLabel("Short description (optional)")).toBeVisible();
    await expect(page.getByLabel("Opening line (optional)")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText(
      "Enter a bot name (at least 2 characters).",
    );

    await page.getByLabel("Short description (optional)").fill("Pre-sales and onboarding helper.");
    await page.getByLabel("Opening line (optional)").fill("Hi there! Tell me what you need.");
    await page.getByLabel("Language (minimal for now)").selectOption("es");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText(
      "Enter a bot name (at least 2 characters).",
    );

    await page.getByLabel("Bot name").fill("Setup Bot");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-channel")).toBeVisible();
  });

  test("knowledge step is honest, skippable, and non-blocking", async ({ page }) => {
    await reachKnowledgeStep(page, "Knowledge Bot");
    await expect(page.getByTestId("wizard-step-knowledge")).toBeVisible();

    await expect(page.getByTestId("knowledge-source-types")).toBeVisible();
    await expect(page.getByText("PDF documents")).toBeVisible();
    await expect(page.getByText("FAQ documents")).toBeVisible();
    await expect(page.getByText("Service information")).toBeVisible();
    await expect(page.getByText("Pricing info")).toBeVisible();
    await expect(page.getByTestId("knowledge-dashboard-path")).toBeVisible();
    await expect(page.getByText("PDFs live on the bot page")).toBeVisible();
    await expect(page.getByTestId("knowledge-dashboard-path").getByRole("link", { name: "Bots" })).toBeVisible();

    await expect(page.getByTestId("wizard-nav-skip")).toBeVisible();
    await expect(page.getByTestId("wizard-nav-next")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-review")).toBeVisible();

    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByTestId("wizard-step-knowledge")).toBeVisible();
    await page.getByTestId("wizard-nav-skip").click();
    await expect(page.getByTestId("wizard-step-review")).toBeVisible();
  });

  test("channel step requires selection, shows Telegram token when needed, and review is last", async ({ page }) => {
    await page.getByText("Education").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByText("Support").click();
    await page.getByTestId("wizard-nav-next").click();
    await page.getByLabel("Bot name").fill("Channel Bot");
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-channel")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-error")).toHaveText(
      "Choose where this bot will be used to continue.",
    );

    await expect(page.getByText("Website widget does not require a Telegram token.")).toBeVisible();
    const channelCards = page.getByTestId("channel-grid").locator("label[data-testid^='channel-card-']");
    await expect(channelCards).toHaveCount(3);
    await expect(page.getByTestId("channel-card-website_widget")).toContainText("Website widget");
    await expect(page.getByTestId("channel-card-telegram")).toContainText("Telegram");
    await expect(page.getByTestId("channel-card-both")).toContainText("Both");

    await page.getByText("Website widget").click();
    await expect(page.locator('input[type="radio"][name="channel"]:checked')).toHaveCount(1);
    await expect(page.getByRole("radio", { name: "Website widget" })).toBeChecked();
    await expect(page.getByTestId("channel-card-website_widget").locator("[data-selected='true']")).toHaveCount(1);

    await page.getByText("Both").click();
    await expect(page.getByTestId("telegram-token-section")).toBeVisible();

    await page.getByTestId("wizard-nav-next").click();
    await page.getByTestId("wizard-nav-next").click();
    await expect(page.getByTestId("wizard-step-review")).toBeVisible();
    await expect(page.getByTestId("review-expected-outcome")).toBeVisible();

    await page.getByTestId("wizard-nav-finish").click();
    await expect(page.getByTestId("wizard-submit-error")).toContainText(
      /Your session expired\. Please sign in and try again\.|Could not create bot right now\. Please try again\.|Unexpected error while creating bot\. Please try again\./,
    );
    await expect(page.getByTestId("wizard-step-error")).toHaveCount(0);
  });

  test("submit shows loading state and server error without fake success", async ({ page }) => {
    await page.route("**/api/v1/bots", async (route, request) => {
      if (request.method() !== "POST") {
        await route.continue();
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 700));
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "internal_error", message: "Internal error" },
        }),
      });
    });

    await reachReviewWithBothChannel(page, "Submit Bot");

    const finish = page.getByTestId("wizard-nav-finish");
    await finish.click();
    await expect(finish).toHaveText("Creating bot...");
    await expect(finish).toBeDisabled();

    await expect(page.getByTestId("wizard-submit-error")).toHaveText(
      "Could not create bot right now. Please try again.",
    );
    await expect(page.getByTestId("wizard-submitting-success")).toHaveCount(0);
  });

  test("submit redirects to bots only after real create response", async ({ page }) => {
    await page.route("**/api/v1/bots", async (route, request) => {
      if (request.method() !== "POST") {
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "bot_created_123",
          status: "active",
          primary_channel: "both",
          name: "Real Submit Bot",
          owner_id: "00000000-0000-4000-8000-000000000001",
          niche_id: "education",
          goal_type: "support",
          welcome_message: null,
          tone: null,
          language: null,
          short_description: null,
          provider_name: "gemini",
          model_name: null,
          temperature: null,
          max_output_tokens: null,
          created_at: "2026-04-09T12:00:00Z",
          updated_at: "2026-04-09T12:00:00Z",
        }),
      });
    });

    await reachReviewWithBothChannel(page, "Real Submit Bot");
    await page.getByTestId("wizard-nav-finish").click();

    await expect(page).toHaveURL(/\/dashboard\/bots\?created=bot_created_123$/);
  });
});
