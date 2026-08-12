import { defineConfig, devices } from "@playwright/test";

/**
 * Real-stack E2E: browser → Next.js → FastAPI → PostgreSQL (no route mocking).
 *
 * Prereqs: migrations applied, `uvicorn app.main:app` on BACKEND_INTERNAL_URL (default :8000),
 * optional `python scripts/seed_e2e_stack.py` for seeded-workspace specs.
 *
 * Run from `frontend/`:
 *   npm run test:e2e:real
 *
 * CI / staging: set E2E_SKIP_WEBSERVER=1 if Next is started separately; set PLAYWRIGHT_BASE_URL
 * to the reachable origin (e.g. https://staging-app.example).
 */
const e2ePort = process.env.E2E_PORT ?? "3002";
const baseURL = (process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${e2ePort}`).replace(/\/$/, "");
const backendInternal = (process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export default defineConfig({
  testDir: "e2e/real-stack",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 25_000 },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  outputDir: "test-results/real-stack",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 25_000,
    navigationTimeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer:
    process.env.E2E_SKIP_WEBSERVER === "1"
      ? undefined
      : {
          command: `npx next dev -p ${e2ePort}`,
          url: baseURL,
          reuseExistingServer: !process.env.CI,
          timeout: 180_000,
          env: {
            ...process.env,
            BACKEND_INTERNAL_URL: backendInternal,
            NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
          },
        },
});
