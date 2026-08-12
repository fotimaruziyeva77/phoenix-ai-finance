import type { Page } from "@playwright/test";

export const AUTH_KEY = "botforge_auth_session_v1";

export const E2E_MOCK_USER = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  email: "e2e@example.com",
  full_name: "E2E User",
  role: "customer_admin",
  is_active: true,
  is_verified: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export type SeedAuthOptions = {
  userOverrides?: Partial<typeof E2E_MOCK_USER>;
  accessToken?: string;
  refreshToken?: string;
};

/**
 * Seeds localStorage with the same shape `AuthProvider` reads (real session path, not a mock guard).
 */
export async function seedAuthSession(page: Page, options?: SeedAuthOptions) {
  const user = { ...E2E_MOCK_USER, ...options?.userOverrides };
  const body = {
    accessToken: options?.accessToken ?? "e2e-seeded-access",
    refreshToken: options?.refreshToken ?? "e2e-seeded-refresh",
    user,
  };
  await page.goto("/");
  await page.evaluate(
    ([key, value]) => {
      window.localStorage.setItem(key, value);
    },
    [AUTH_KEY, JSON.stringify(body)] as const,
  );
}

export async function clearAuthSession(page: Page) {
  await page.goto("/");
  await page.evaluate((key) => window.localStorage.removeItem(key), AUTH_KEY);
}
