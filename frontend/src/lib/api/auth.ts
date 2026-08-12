import type { AuthBootstrap, AuthSession, MeUser, TokenPairResponse } from "@/types/auth";

import { apiFetch, apiFetchWithAuth } from "./client";

export type { AuthBootstrap } from "@/types/auth";

export async function registerAccount(body: {
  email: string;
  password: string;
  full_name?: string | null;
}): Promise<AuthSession> {
  return apiFetch<AuthSession>("/api/v1/auth/register", {
    method: "POST",
    body,
  });
}

export async function loginWithEmail(body: {
  email: string;
  password: string;
}): Promise<AuthSession> {
  return apiFetch<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    body,
  });
}

export async function exchangeOAuthCode(exchangeCode: string): Promise<AuthSession> {
  return apiFetch<AuthSession>("/api/v1/auth/oauth/exchange", {
    method: "POST",
    body: { exchange_code: exchangeCode },
  });
}

export async function fetchCurrentUser(accessToken: string | null): Promise<MeUser> {
  return apiFetchWithAuth<MeUser>("/api/v1/auth/me", accessToken, {
    method: "GET",
  });
}

export async function fetchAuthBootstrap(): Promise<AuthBootstrap> {
  return apiFetch<AuthBootstrap>("/api/v1/auth/bootstrap", { method: "GET" });
}

/** Rotate cookies / tokens (body optional when refresh is HttpOnly cookie). */
export async function refreshAuthSession(body?: { refresh_token?: string }): Promise<TokenPairResponse> {
  return apiFetch<TokenPairResponse>("/api/v1/auth/refresh", {
    method: "POST",
    body: body?.refresh_token ? { refresh_token: body.refresh_token } : {},
  });
}

/** POST /api/v1/auth/forgot-password — sends reset email (always 204, no token returned). */
export async function forgotPassword(email: string): Promise<void> {
  await apiFetch<void>("/api/v1/auth/forgot-password", {
    method: "POST",
    body: { email },
  });
}

/** POST /api/v1/auth/change-password — authenticated in-app password change. */
export async function changePassword(
  accessToken: string | null,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await apiFetchWithAuth<void>("/api/v1/auth/change-password", accessToken, {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

/** POST /api/v1/auth/reset-password — consumes token + sets new password. */
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiFetch<void>("/api/v1/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });
}

/** PATCH /api/v1/auth/me — update mutable profile fields. */
export async function updateProfile(
  accessToken: string | null,
  data: { full_name: string | null },
): Promise<MeUser> {
  return apiFetchWithAuth<MeUser>("/api/v1/auth/me", accessToken, {
    method: "PATCH",
    body: data,
  });
}

export function oauthStartUrl(provider: "google" | "github"): string {
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
  return `${base}/api/v1/auth/${provider}/start`;
}
