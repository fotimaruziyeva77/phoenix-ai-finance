import { expect, test } from "@playwright/test";

/**
 * Real product path: marketing landing → signup form → authenticated dashboard.
 *
 * Requires FastAPI with PostgreSQL (migrations applied). Browser calls same-origin `/api/*`;
 * Next.js rewrites to the backend (default `127.0.0.1:8000` when NEXT_PUBLIC_API_BASE_URL is empty).
 *
 * Enable with either:
 * - `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` (matches other real-backend specs), or
 * - `E2E_REAL_BACKEND=1` when the rewrite target is already correct for your environment.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const realBackend = Boolean(API_BASE || process.env.E2E_REAL_BACKEND === "1");

test.describe("MVP landing → signup → dashboard (real backend)", () => {
  test.skip(!realBackend, "Set NEXT_PUBLIC_API_BASE_URL or E2E_REAL_BACKEND=1 with API + DB running.");

  test("Create Your Bot CTA leads to signup; new user reaches dashboard overview", async ({ page }) => {
    const email = `mvp-e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;

    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: /AI that brings you real clients/ })).toBeVisible();
    await page.getByRole("link", { name: "Create Your Bot" }).click();
    await expect(page).toHaveURL(/\/signup$/);
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();

    await page.locator("#signup-name").fill("MVP E2E User");
    await page.locator("#signup-email").fill(email);
    await page.locator("#signup-password").fill("password123");
    await page.locator("#signup-confirm").fill("password123");
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/dashboard\/?$/);
    await expect(page.getByRole("heading", { name: /^Hi, MVP$/ })).toBeVisible();
    await expect(page.getByText("This is your workspace hub.", { exact: false })).toBeVisible();
  });
});
