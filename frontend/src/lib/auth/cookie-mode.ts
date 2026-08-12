/**
 * When true, the SPA uses ``credentials: 'include'`` and CSRF headers instead of
 * storing tokens in localStorage (must match API ``APP_AUTH_COOKIE_ENABLED``).
 */
export function authCookieMode(): boolean {
  return process.env.NEXT_PUBLIC_AUTH_COOKIE_MODE === "true";
}

export function authCsrfHeaderName(): string {
  return process.env.NEXT_PUBLIC_AUTH_CSRF_HEADER_NAME?.trim() || "X-CSRF-Token";
}
