import * as fs from "node:fs";
import * as path from "node:path";

import type { Page } from "@playwright/test";

import { AUTH_KEY } from "../helpers/auth-storage";

export type E2eSeedOutput = {
  email: string;
  password: string;
  full_name: string;
  user_id: string;
  support_bot_id: string;
  sales_bot_id: string;
  support_bot_name: string;
  sales_bot_name: string;
  widget_public_key: string;
  lead_name: string;
};

const CREATE_BOT_DRAFT_KEY = "botforge_create_bot_draft_v1";

export function loadSeedOutput(): E2eSeedOutput | null {
  const envPath = process.env.E2E_SEED_OUTPUT_PATH?.trim();
  const defaultPath = path.join(__dirname, "seed-output.json");
  const p = envPath && envPath.length > 0 ? path.resolve(envPath) : defaultPath;
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf8")) as E2eSeedOutput;
  } catch {
    return null;
  }
}

export async function clearBrowserWorkspaceState(page: Page) {
  await page.goto("/");
  await page.evaluate(
    ([authKey, draftKey]) => {
      window.localStorage.removeItem(authKey);
      window.localStorage.removeItem(draftKey);
    },
    [AUTH_KEY, CREATE_BOT_DRAFT_KEY] as const,
  );
}

export async function loginWithEmailPassword(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 60_000 });
}

/** Same-origin API base for ``request`` calls (Next rewrites /api when NEXT_PUBLIC_API_BASE_URL is empty). */
export function apiOriginFromPlaywrightBase(baseURL: string): string {
  return baseURL.replace(/\/$/, "");
}
