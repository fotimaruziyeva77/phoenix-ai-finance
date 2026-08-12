import { describe, expect, it } from "vitest";

import {
  buildLoginRedirectUrl,
  DEFAULT_AUTHENTICATED_ENTRY,
  isSafeInternalNextPath,
  LOGIN_PATH,
  resolvePostAuthRedirect,
} from "./route-redirect";

/** Used by AuthGate / GuestGate. End-to-end: `e2e/protected-routing.spec.ts`. */

describe("isSafeInternalNextPath", () => {
  it("allows internal paths", () => {
    expect(isSafeInternalNextPath("/dashboard")).toBe(true);
    expect(isSafeInternalNextPath("/dashboard/settings")).toBe(true);
  });

  it("rejects open redirects and protocols", () => {
    expect(isSafeInternalNextPath("//evil.com")).toBe(false);
    expect(isSafeInternalNextPath("https://evil.com")).toBe(false);
    expect(isSafeInternalNextPath("javascript:alert(1)")).toBe(false);
    expect(isSafeInternalNextPath("")).toBe(false);
  });
});

describe("resolvePostAuthRedirect", () => {
  it("uses next when safe", () => {
    expect(resolvePostAuthRedirect("/dashboard/bots")).toBe("/dashboard/bots");
  });

  it("falls back when unsafe or missing", () => {
    expect(resolvePostAuthRedirect(null)).toBe(DEFAULT_AUTHENTICATED_ENTRY);
    expect(resolvePostAuthRedirect("//x")).toBe(DEFAULT_AUTHENTICATED_ENTRY);
  });
});

describe("buildLoginRedirectUrl", () => {
  it("encodes return path", () => {
    const url = buildLoginRedirectUrl("/dashboard?tab=1");
    const parsed = new URL(url, "http://local.test");
    expect(parsed.pathname).toBe(LOGIN_PATH);
    expect(parsed.searchParams.get("next")).toBe("/dashboard?tab=1");
  });

  it("uses dashboard when return path unsafe", () => {
    const url = buildLoginRedirectUrl("//evil");
    expect(url).toContain(encodeURIComponent(DEFAULT_AUTHENTICATED_ENTRY));
  });
});
