/**
 * Central auth routing helpers (client-side session from storage + API — no hardcoded users).
 */

export const LOGIN_PATH = "/login" as const;
export const SIGNUP_PATH = "/signup" as const;
export const DEFAULT_AUTHENTICATED_ENTRY = "/dashboard" as const;

/** Blocks open redirects and protocol-relative URLs. */
export function isSafeInternalNextPath(path: string): boolean {
  if (!path) return false;
  if (!path.startsWith("/")) return false;
  if (path.startsWith("//")) return false;
  if (path.includes("://")) return false;
  return true;
}

/**
 * Where to send the user after a successful sign-in or sign-up.
 * `next` must be a safe same-origin path from the query string.
 */
export function resolvePostAuthRedirect(
  nextParam: string | null | undefined,
  fallback: string = DEFAULT_AUTHENTICATED_ENTRY,
): string {
  if (nextParam != null && isSafeInternalNextPath(nextParam)) {
    return nextParam;
  }
  return fallback;
}

/**
 * Login URL that returns the user to `returnPath` after authentication.
 * Falls back to dashboard if `returnPath` is missing or unsafe.
 */
export function buildLoginRedirectUrl(returnPath: string): string {
  const target =
    returnPath && isSafeInternalNextPath(returnPath) ? returnPath : DEFAULT_AUTHENTICATED_ENTRY;
  return `${LOGIN_PATH}?next=${encodeURIComponent(target)}`;
}
