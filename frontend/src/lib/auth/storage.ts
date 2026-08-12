import type { StoredAuthSession } from "@/types/auth";

import { AUTH_STORAGE_KEY } from "./constants";

export function readStoredSession(): StoredAuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const o = parsed as Record<string, unknown>;
    if (
      typeof o.accessToken !== "string" ||
      typeof o.refreshToken !== "string" ||
      !o.user ||
      typeof o.user !== "object"
    ) {
      return null;
    }
    return parsed as StoredAuthSession;
  } catch {
    return null;
  }
}

export function writeStoredSession(session: StoredAuthSession): void {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession(): void {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}
