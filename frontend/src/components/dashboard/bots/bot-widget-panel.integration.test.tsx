/**
 * Integration-style tests: real useBotWidget + bot-widget API module, HTTP mocked at fetch.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BotWidgetPanel } from "./bot-widget-panel";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/hooks/useAuth";

const BOT_ID = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb";

/** Single source of truth for GET / PATCH responses — assertions use this object, not unrelated literals. */
const serverWidgetConfig = {
  id: "wwwwwwww-wwww-4www-wwww-wwwwwwwwwwww",
  bot_id: BOT_ID,
  public_widget_key: "pk_live_from_backend_7f3a",
  is_enabled: true,
  allowed_domains: ["shop.example.com", "www.shop.example.com"],
  theme: "light" as string | null,
  welcome_text: "Hello from the server" as string | null,
  widget_settings: null as Record<string, unknown> | null,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

function authValue() {
  return {
    user: null,
    accessToken: "integration-test-token",
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

describe("BotWidgetPanel integration (fetch + useBotWidget)", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue(authValue());
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:9999");
    vi.stubEnv("NEXT_PUBLIC_WIDGET_SCRIPT_URL", "https://cdn.integration.test/widget.js");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("loads widget config from backend and renders server fields (no invented key)", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      expect(url).toContain(`/api/v1/bots/${BOT_ID}/widget`);
      expect(init?.headers).toBeDefined();
      const auth = new Headers(init?.headers as HeadersInit).get("Authorization");
      expect(auth).toBe("Bearer integration-test-token");
      if ((init?.method ?? "GET").toUpperCase() === "GET") {
        return jsonResponse(serverWidgetConfig);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<BotWidgetPanel botId={BOT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("bot-widget-public-key")).toHaveTextContent(serverWidgetConfig.public_widget_key);
    });

    expect(screen.getByTestId("bot-widget-domains")).toHaveValue(
      serverWidgetConfig.allowed_domains.join("\n"),
    );
    expect(screen.getByTestId("bot-widget-welcome")).toHaveValue(serverWidgetConfig.welcome_text);

    const snippetText = screen.getByTestId("bot-widget-snippet").textContent ?? "";
    expect(snippetText).toContain(`publicKey: "${serverWidgetConfig.public_widget_key}"`);
    expect(snippetText).toContain("http://127.0.0.1:9999");
    expect(snippetText).toContain("https://cdn.integration.test/widget.js");
    expect(snippetText).toContain("BotforgeWidget.init");
  });

  it("PATCH save sends backend-shaped body and UI reflects PATCH response", async () => {
    const updated = {
      ...serverWidgetConfig,
      is_enabled: false,
      allowed_domains: ["app.example.com"],
      theme: null,
      welcome_text: "Patched by server",
      updated_at: "2026-03-02T15:00:00.000Z",
    };

    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET") {
        return jsonResponse(serverWidgetConfig);
      }
      if (method === "PATCH") {
        const body = JSON.parse(init?.body as string) as Record<string, unknown>;
        expect(body).toEqual({
          is_enabled: false,
          allowed_domains_json: ["only.send.com"],
          theme: null,
          welcome_text: "user typed welcome",
        });
        return jsonResponse(updated);
      }
      return new Response("bad", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotWidgetPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-widget-panel");

    await user.click(screen.getByTestId("bot-widget-enabled-switch"));
    await user.clear(screen.getByTestId("bot-widget-domains"));
    await user.type(screen.getByTestId("bot-widget-domains"), "only.send.com");
    await user.selectOptions(screen.getByTestId("bot-widget-theme"), "");
    await user.clear(screen.getByTestId("bot-widget-welcome"));
    await user.type(screen.getByTestId("bot-widget-welcome"), "user typed welcome");

    await user.click(screen.getByTestId("bot-widget-save-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-widget-save-success")).toHaveTextContent(/saved/i);
    });

    expect(screen.getByTestId("bot-widget-welcome")).toHaveValue(updated.welcome_text);
    expect(screen.getByTestId("bot-widget-domains")).toHaveValue(updated.allowed_domains.join("\n"));
    expect(screen.getByTestId("bot-widget-snippet")).toHaveTextContent(updated.public_widget_key);
  });

  it("copy snippet writes exact rendered snippet to clipboard", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(serverWidgetConfig));
    vi.stubGlobal("fetch", fetchMock);

    const writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);

    const user = userEvent.setup();
    render(<BotWidgetPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-widget-snippet");
    const rendered = screen.getByTestId("bot-widget-snippet").textContent ?? "";

    await user.click(screen.getByTestId("bot-widget-copy-snippet"));

    await waitFor(() => {
      expect(writeTextSpy).toHaveBeenCalledWith(rendered);
    });

    writeTextSpy.mockRestore();
  });

  it("shows PATCH error from server without showing save success", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET") {
        return jsonResponse(serverWidgetConfig);
      }
      if (method === "PATCH") {
        return jsonResponse({ error: { message: "Domain list invalid" } }, 400);
      }
      return new Response("bad", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotWidgetPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-widget-panel");
    await user.click(screen.getByTestId("bot-widget-save-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-widget-save-error")).toHaveTextContent("Domain list invalid");
    });
    expect(screen.queryByTestId("bot-widget-save-success")).not.toBeInTheDocument();
  });

  it("shows load error and recovers after retry refetches GET", async () => {
    let getAttempts = 0;
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      if (method !== "GET") {
        return new Response("nope", { status: 500 });
      }
      getAttempts += 1;
      if (getAttempts === 1) {
        return new Response("upstream", { status: 503 });
      }
      return jsonResponse(serverWidgetConfig);
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotWidgetPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-widget-load-error");
    expect(screen.getByTestId("bot-widget-load-error")).toHaveTextContent(/could not load widget settings/i);

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByTestId("bot-widget-public-key")).toHaveTextContent(serverWidgetConfig.public_widget_key);
    });
    expect(getAttempts).toBe(2);
  });
});
