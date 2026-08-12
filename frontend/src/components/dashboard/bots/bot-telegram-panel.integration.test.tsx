/**
 * Integration-style tests: real useBotTelegram + bot-telegram API module, HTTP mocked at fetch.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BotTelegramPanel } from "./bot-telegram-panel";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/hooks/useAuth";

const BOT_ID = "cccccccc-cccc-4ccc-cccc-cccccccccccc";

/** Backend-shaped disconnected snapshot (BotTelegramStatusResponse). */
const statusDisconnected = {
  channel_status: "draft" as const,
  configured: false,
  connected: false,
  bot_username: null,
  last_verified_at: null,
  webhook_url_configured: false,
  last_error_code: null,
};

/** Populated only from a mocked successful POST /connect response — not invented in the UI. */
const statusConnectedFromServer = {
  channel_status: "active" as const,
  configured: true,
  connected: true,
  bot_username: "acme_bot_from_api",
  last_verified_at: "2026-04-08T14:30:00.000Z",
  webhook_url_configured: true,
  last_error_code: null,
};

/** Token used only client-side; must never appear in mocked JSON responses. */
const VALID_STYLE_TOKEN = "1234567890:AA_integration_valid_token_suffix_not_from_server";

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

/** Response bodies and DOM must never echo the user token (request body will contain it by design). */
function assertJsonHasNoTokenLeak(json: string, token: string) {
  expect(json).not.toContain(token);
  expect(json).not.toContain("AA_integration_valid_token");
}

describe("BotTelegramPanel integration (fetch + useBotTelegram)", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue(authValue());
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://127.0.0.1:9998");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it("loads status and renders connect form (token field, BotFather guidance, actions)", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      expect(url).toContain(`/api/v1/bots/${BOT_ID}/telegram/status`);
      const auth = new Headers(init?.headers as HeadersInit).get("Authorization");
      expect(auth).toBe("Bearer integration-test-token");
      if ((init?.method ?? "GET").toUpperCase() === "GET") {
        return jsonResponse(statusDisconnected);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<BotTelegramPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-telegram-panel");

    expect(screen.getByTestId("bot-telegram-botfather-note")).toHaveTextContent(/BotFather/i);
    expect(screen.getByTestId("bot-telegram-token-input")).toBeInTheDocument();
    expect(screen.getByTestId("bot-telegram-connect")).toBeInTheDocument();
    expect(screen.getByTestId("bot-telegram-disconnect")).toBeDisabled();
    expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent(/not started/i);
  });

  it("valid connect sends trimmed token and UI shows only server-returned username; input cleared after save", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/telegram/status")) {
        return jsonResponse(statusDisconnected);
      }
      if (method === "POST" && url.includes("/telegram/connect")) {
        const raw = init?.body as string;
        const body = JSON.parse(raw) as { bot_token: string };
        expect(body).toEqual({ bot_token: VALID_STYLE_TOKEN.trim() });
        const resBody = { ...statusConnectedFromServer };
        const encoded = JSON.stringify(resBody);
        assertJsonHasNoTokenLeak(encoded, VALID_STYLE_TOKEN);
        return jsonResponse(resBody);
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotTelegramPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-telegram-panel");

    const tokenInput = screen.getByTestId("bot-telegram-token-input");
    await user.type(tokenInput, `  ${VALID_STYLE_TOKEN}  `);
    await user.click(screen.getByTestId("bot-telegram-connect"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent(/active/i);
    });

    expect(screen.getByTestId("bot-telegram-username")).toHaveTextContent(
      `@${statusConnectedFromServer.bot_username}`,
    );
    expect(screen.getByTestId("bot-telegram-webhook-hint")).toHaveTextContent(/webhook registered/i);
    expect(screen.getByTestId("bot-telegram-token-input")).toHaveValue("");
    expect(document.body.textContent).not.toContain(VALID_STYLE_TOKEN.trim());
    expect(document.body.textContent).not.toContain("AA_integration_valid_token");
  });

  it("invalid token shows API error and does not show success or fake username", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/telegram/status")) {
        return jsonResponse(statusDisconnected);
      }
      if (method === "POST" && url.includes("/telegram/connect")) {
        return jsonResponse(
          {
            error: {
              code: "telegram_token_invalid",
              message: "Telegram rejected this bot token. Check BotFather and try again.",
            },
          },
          400,
        );
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotTelegramPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-telegram-panel");

    await user.type(screen.getByTestId("bot-telegram-token-input"), VALID_STYLE_TOKEN);
    await user.click(screen.getByTestId("bot-telegram-connect"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-telegram-action-error")).toHaveTextContent(
        /Telegram rejected this bot token/i,
      );
    });

    expect(screen.queryByTestId("bot-telegram-success")).not.toBeInTheDocument();
    expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent(/not started/i);
    expect(screen.queryByTestId("bot-telegram-username")).not.toBeInTheDocument();
  });

  it("connected status from GET renders server username and verified time only", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(statusConnectedFromServer));
    vi.stubGlobal("fetch", fetchMock);

    render(<BotTelegramPanel botId={BOT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("bot-telegram-username")).toHaveTextContent(
        `@${statusConnectedFromServer.bot_username}`,
      );
    });

    expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent(/active/i);
    expect(screen.getByTestId("bot-telegram-last-verified")).toHaveTextContent(/2026/i);
  });

  it("disconnect sends POST then refetches GET; UI returns to not connected", async () => {
    let phase: "connected" | "disconnected" = "connected";

    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "GET" && url.includes("/telegram/status")) {
        return jsonResponse(phase === "connected" ? statusConnectedFromServer : statusDisconnected);
      }
      if (method === "POST" && url.includes("/telegram/disconnect")) {
        expect(url).toContain(`/api/v1/bots/${BOT_ID}/telegram/disconnect`);
        phase = "disconnected";
        return new Response(null, { status: 204 });
      }
      return new Response("unexpected", { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotTelegramPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-telegram-username");

    await user.click(screen.getByTestId("bot-telegram-disconnect"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent(/not started/i);
    });

    const disconnectCalls = fetchMock.mock.calls.filter(
      (c) =>
        requestUrl(c[0] as RequestInfo).includes("/telegram/disconnect") &&
        ((c[1] as RequestInit)?.method ?? "POST").toUpperCase() === "POST",
    );
    expect(disconnectCalls.length).toBe(1);

    const statusCalls = fetchMock.mock.calls.filter((c) =>
      requestUrl(c[0] as RequestInfo).includes("/telegram/status"),
    );
    expect(statusCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("load error and retry issues second GET", async () => {
    let getAttempts = 0;
    const fetchMock = vi.fn().mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = (init?.method ?? "GET").toUpperCase();
      if (method !== "GET") {
        return new Response("nope", { status: 500 });
      }
      const url = requestUrl(input);
      if (!url.includes("/telegram/status")) {
        return new Response("bad", { status: 500 });
      }
      getAttempts += 1;
      if (getAttempts === 1) {
        return new Response("upstream", { status: 503 });
      }
      return jsonResponse(statusDisconnected);
    });
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<BotTelegramPanel botId={BOT_ID} />);

    await screen.findByTestId("bot-telegram-load-error");

    await user.click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByTestId("bot-telegram-panel")).toBeInTheDocument();
    });

    expect(within(screen.getByTestId("bot-telegram-panel")).getByTestId("bot-telegram-token-input")).toBeInTheDocument();
    expect(getAttempts).toBe(2);
  });
});
