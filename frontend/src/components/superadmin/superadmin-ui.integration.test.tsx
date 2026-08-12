/**
 * Superadmin UI integration: mocked fetch only; assertions use shared fixtures (no unrelated literals).
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SuperadminBotDetail } from "./superadmin-bot-detail";
import { SuperadminBotsList } from "./superadmin-bots-list";
import { SuperadminOverview } from "./superadmin-overview";
import { SuperadminUserDetail } from "./superadmin-user-detail";
import { SuperadminUsersList } from "./superadmin-users-list";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/hooks/useAuth";

const API_BASE = "http://127.0.0.1:9999";
const ACCESS = "integration-superadmin-token";

/** Backend-shaped totals returned by list endpoints (limit=1 probes). */
const OVERVIEW_TOTALS = {
  users: 100,
  users_active: 88,
  bots: 40,
  bots_suspended: 2,
} as const;

const LIST_USER = {
  id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
  email: "tenant@fixture.test",
  full_name: "Fixture Tenant",
  role: "customer_admin",
  is_active: true,
  is_verified: true,
  suspended_at: null,
  has_password: true,
  oauth_provider_count: 0,
  bot_count: 3,
  created_at: "2026-02-01T10:00:00.000Z",
  updated_at: "2026-02-10T12:00:00.000Z",
} as const;

const LIST_BOT = {
  id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
  owner_id: LIST_USER.id,
  owner_email: LIST_USER.email,
  name: "Fixture Bot Alpha",
  niche_id: "retail",
  goal_type: "sales",
  status: "active",
  provider_name: "gemini",
  model_name: "gemini-pro",
  widget_configured: true,
  telegram_connected: false,
  platform_suspended_at: null,
  created_at: "2026-02-02T10:00:00.000Z",
  updated_at: "2026-02-11T12:00:00.000Z",
} as const;

const USER_DETAIL_ACTIVE = {
  ...LIST_USER,
  suspension_reason: null,
  oauth_providers: [] as { provider: string }[],
} as const;

const USER_DETAIL_SUSPENDED = {
  ...USER_DETAIL_ACTIVE,
  is_active: false,
  suspended_at: "2026-03-01T15:00:00.000Z",
  suspension_reason: "e2e-policy",
} as const;

const BOT_DETAIL_ACTIVE = {
  ...LIST_BOT,
  platform_suspension_reason: null,
  welcome_message: "Hi",
  tone: null,
  language: null,
  short_description: null,
  temperature: 0.4,
  max_output_tokens: 512,
} as const;

const BOT_DETAIL_SUSPENDED = {
  ...BOT_DETAIL_ACTIVE,
  platform_suspended_at: "2026-03-02T16:00:00.000Z",
  platform_suspension_reason: "operator-hold",
} as const;

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function superadminAuth() {
  return {
    user: {
      id: "99999999-9999-4999-9999-999999999999",
      email: "super@fixture.test",
      full_name: "Super Fixture",
      role: "superadmin",
      is_active: true,
      is_verified: true,
      created_at: "2026-01-01T00:00:00.000Z",
      updated_at: "2026-01-01T00:00:00.000Z",
    },
    accessToken: ACCESS,
    refreshToken: null,
    canUseAuthenticatedApi: true,
    hydrated: true,
    busy: false,
    login: vi.fn(),
    register: vi.fn(),
    completeOAuthExchange: vi.fn(),
    logout: vi.fn(),
    refreshProfile: vi.fn(),
  };
}

describe("Superadmin UI (fetch-mocked)", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue(superadminAuth());
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", API_BASE);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("overview renders totals from four list probes (no invented numbers)", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      expect(url.startsWith(`${API_BASE}/`)).toBe(true);
      expect((init?.headers as Headers)?.get?.("Authorization")).toBe(`Bearer ${ACCESS}`);
      expect((init?.method ?? "GET").toUpperCase()).toBe("GET");
      if (url.includes("/api/v1/admin/users")) {
        const total = url.includes("is_active=true") ? OVERVIEW_TOTALS.users_active : OVERVIEW_TOTALS.users;
        return jsonResponse({ items: [], total, limit: 1, offset: 0 });
      }
      if (url.includes("/api/v1/admin/bots")) {
        const total = url.includes("platform_suspended=true")
          ? OVERVIEW_TOTALS.bots_suspended
          : OVERVIEW_TOTALS.bots;
        return jsonResponse({ items: [], total, limit: 1, offset: 0 });
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminOverview />);

    await waitFor(() => {
      expect(screen.getByTestId("superadmin-overview-total-users")).toHaveTextContent(
        String(OVERVIEW_TOTALS.users),
      );
    });
    expect(screen.getByTestId("superadmin-overview-active-users")).toHaveTextContent(
      String(OVERVIEW_TOTALS.users_active),
    );
    expect(screen.getByTestId("superadmin-overview-total-bots")).toHaveTextContent(String(OVERVIEW_TOTALS.bots));
    expect(screen.getByTestId("superadmin-overview-suspended-bots")).toHaveTextContent(
      String(OVERVIEW_TOTALS.bots_suspended),
    );
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("users list renders row email from API items", async () => {
    const listPayload = {
      items: [LIST_USER],
      total: 1,
      limit: 25,
      offset: 0,
    };
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/api/v1/admin/users?") && url.includes("limit=25")) {
        return jsonResponse(listPayload);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminUsersList />);

    await waitFor(() => {
      expect(screen.getByTestId("superadmin-users-table")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: LIST_USER.email })).toHaveAttribute(
      "href",
      `/superadmin/users/${LIST_USER.id}`,
    );
  });

  it("bots list renders bot name from API items", async () => {
    const listPayload = {
      items: [LIST_BOT],
      total: 1,
      limit: 25,
      offset: 0,
    };
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/api/v1/admin/bots?") && url.includes("limit=25")) {
        return jsonResponse(listPayload);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminBotsList />);

    await waitFor(() => {
      expect(screen.getByTestId("superadmin-bots-table")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: LIST_BOT.name })).toHaveAttribute(
      "href",
      `/superadmin/bots/${LIST_BOT.id}`,
    );
  });

  it("user detail suspend posts backend-shaped body and UI matches POST response", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.endsWith(`/api/v1/admin/users/${LIST_USER.id}`)) {
        return jsonResponse(USER_DETAIL_ACTIVE);
      }
      if (method === "POST" && url.endsWith(`/api/v1/admin/users/${LIST_USER.id}/suspend`)) {
        const body = JSON.parse(init?.body as string) as { reason?: string };
        expect(body).toEqual({ reason: "spam-case" });
        return jsonResponse(USER_DETAIL_SUSPENDED);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminUserDetail userId={LIST_USER.id} />);

    await waitFor(() => {
      expect(screen.getByText(USER_DETAIL_ACTIVE.email)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Suspend user" }));
    await user.type(screen.getByPlaceholderText(/Internal note/i), "spam-case");
    await user.click(screen.getByRole("button", { name: "Suspend" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Activate user" })).toBeInTheDocument();
    });
    expect(screen.getByText("User suspended.")).toBeInTheDocument();
  });

  it("bot detail platform-suspend posts optional reason and UI matches response", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.endsWith(`/api/v1/admin/bots/${LIST_BOT.id}`)) {
        return jsonResponse(BOT_DETAIL_ACTIVE);
      }
      if (method === "POST" && url.endsWith(`/api/v1/admin/bots/${LIST_BOT.id}/suspend`)) {
        const body = JSON.parse(init?.body as string) as { reason?: string };
        expect(body).toEqual({ reason: "tos" });
        return jsonResponse(BOT_DETAIL_SUSPENDED);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminBotDetail botId={LIST_BOT.id} />);

    await waitFor(() => {
      expect(screen.getByText(BOT_DETAIL_ACTIVE.name)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Platform-suspend bot" }));
    await user.type(screen.getByPlaceholderText(/Internal note/i), "tos");
    await user.click(screen.getByRole("button", { name: "Suspend bot" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Clear platform suspension" })).toBeInTheDocument();
    });
    expect(screen.getByText("Bot platform-suspended.")).toBeInTheDocument();
  });

  it("bot detail activate clears suspension via POST activate", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.endsWith(`/api/v1/admin/bots/${LIST_BOT.id}`)) {
        return jsonResponse(BOT_DETAIL_SUSPENDED);
      }
      if (method === "POST" && url.endsWith(`/api/v1/admin/bots/${LIST_BOT.id}/activate`)) {
        expect(init?.body).toBe(JSON.stringify({}));
        return jsonResponse(BOT_DETAIL_ACTIVE);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<SuperadminBotDetail botId={LIST_BOT.id} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Clear platform suspension" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Clear platform suspension" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Platform-suspend bot" })).toBeInTheDocument();
    });
  });
});
