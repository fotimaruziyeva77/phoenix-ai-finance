import { describe, expect, it } from "vitest";

import type { AuthBootstrap, AuthSession, MeUser, TokenPairResponse } from "./auth";

/** Minimal JSON-shaped samples — must stay aligned with Pydantic models / OpenAPI. */
describe("auth API contract (frontend types)", () => {
  it("accepts bearer AuthSession", () => {
    const s = {
      auth_transport: "bearer",
      user: {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "u@example.com",
        full_name: null,
        role: "customer_admin",
        is_active: true,
        is_verified: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      access_token: "a",
      refresh_token: "r",
      token_type: "Bearer",
      expires_in: 3600,
    } satisfies AuthSession;
    expect(s.auth_transport).toBe("bearer");
  });

  it("accepts cookie-mode session with omitted tokens", () => {
    const s = {
      auth_transport: "cookie",
      user: {
        id: "550e8400-e29b-41d4-a716-446655440000",
        email: "u@example.com",
        full_name: null,
        role: "customer_admin",
        is_active: true,
        is_verified: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      access_token: null,
      refresh_token: null,
      token_type: "Bearer",
      expires_in: 900,
      csrf_token: "csrf",
    } satisfies AuthSession;
    expect(s.access_token).toBeNull();
  });

  it("accepts TokenPairResponse", () => {
    const t = {
      auth_transport: "bearer",
      access_token: "a",
      refresh_token: "r",
      token_type: "Bearer",
      expires_in: 60,
    } satisfies TokenPairResponse;
    expect(t.expires_in).toBe(60);
  });

  it("accepts MeUser with reserved null fields", () => {
    const m = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      email: "u@example.com",
      full_name: null,
      role: "customer_admin",
      is_active: true,
      is_verified: false,
      has_password: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      email_verified_at: null,
      plan_key: null,
    } satisfies MeUser;
    expect(m.plan_key).toBeNull();
  });

  it("accepts AuthBootstrap", () => {
    const b = {
      authenticated: false,
      auth_transport: "none",
      user: null,
      csrf_token: null,
    } satisfies AuthBootstrap;
    expect(b.authenticated).toBe(false);
  });
});
