/**
 * Wizard + mocked fetch: asserts POST body includes initial_channel and honest success UI by status.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { NicheCatalogProvider } from "@/contexts/niche-catalog-context";
import { useAuth } from "@/hooks/useAuth";
import { EMERGENCY_NICHE_CATALOG_ITEMS } from "@/lib/bot-domain/niche-emergency-fallback";

import { CreateBotWizard } from "./create-bot-wizard";

const TEST_NICHE_CATALOG = { schema_version: 1 as const, niches: EMERGENCY_NICHE_CATALOG_ITEMS };

function renderWizard() {
  return render(
    <NicheCatalogProvider initialData={TEST_NICHE_CATALOG}>
      <CreateBotWizard />
    </NicheCatalogProvider>,
  );
}

function authValue() {
  return {
    user: null,
    accessToken: "wizard-integration-token",
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

describe("CreateBotWizard integration (fetch)", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue(authValue() as ReturnType<typeof useAuth>);
    localStorage.clear();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("POST /bots includes initial_channel web and shows active success copy", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.includes("/api/v1/bots") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        expect(body.initial_channel).toBe("web");
        expect(body).not.toHaveProperty("telegram_bot_token");
        return new Response(
          JSON.stringify({
            id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            status: "active",
            primary_channel: "web",
            name: "Integration Bot",
            owner_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
            niche_id: "education",
            goal_type: "support",
            welcome_message: null,
            tone: null,
            language: "en",
            short_description: null,
            provider_name: "gemini",
            model_name: null,
            temperature: null,
            max_output_tokens: null,
            created_at: "2026-04-09T12:00:00Z",
            updated_at: "2026-04-09T12:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    });
    globalThis.fetch = fetchMock as typeof fetch;

    const user = userEvent.setup();
    renderWizard();

    await screen.findByTestId("wizard-step-niche");
    await user.click(screen.getByText("Education"));
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-goal");
    await user.click(screen.getByText("Support"));
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-basics");
    await user.type(screen.getByLabelText("Bot name"), "Integration Bot");
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-channel");
    await user.click(screen.getByText("Website widget"));
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-knowledge");
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-review");
    await user.click(screen.getByTestId("wizard-nav-finish"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    await screen.findByTestId("wizard-submitting-success");
    expect(screen.getByTestId("wizard-success-status-line").textContent).toContain("active");
    expect(screen.getByTestId("wizard-submitting-success")).toHaveAttribute("data-created-status", "active");
  });

  it("POST /bots includes telegram_bot_token when provided and surfaces channel_pending success", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.includes("/api/v1/bots") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        expect(body.initial_channel).toBe("telegram");
        expect(body.telegram_bot_token).toBe("1234567890:AA_valid_len_token_x");
        return new Response(
          JSON.stringify({
            id: "dddddddd-dddd-4ddd-dddd-dddddddddddd",
            status: "channel_pending",
            primary_channel: "telegram",
            name: "TG Bot",
            owner_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
            niche_id: "education",
            goal_type: "support",
            welcome_message: null,
            tone: null,
            language: null,
            short_description: null,
            provider_name: "gemini",
            model_name: null,
            temperature: null,
            max_output_tokens: null,
            created_at: "2026-04-09T12:00:00Z",
            updated_at: "2026-04-09T12:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    });
    globalThis.fetch = fetchMock as typeof fetch;

    const user = userEvent.setup();
    renderWizard();

    await screen.findByTestId("wizard-step-niche");
    await user.click(screen.getByText("Education"));
    await user.click(screen.getByTestId("wizard-nav-next"));
    await user.click(screen.getByText("Support"));
    await user.click(screen.getByTestId("wizard-nav-next"));
    await user.type(screen.getByLabelText("Bot name"), "TG Bot");
    await user.click(screen.getByTestId("wizard-nav-next"));

    await screen.findByTestId("wizard-step-channel");
    await user.click(screen.getByText("Telegram"));
    await user.type(screen.getByTestId("telegram-bot-token-input"), "1234567890:AA_valid_len_token_x");
    await user.click(screen.getByTestId("wizard-nav-next"));
    await user.click(screen.getByTestId("wizard-nav-next"));
    await screen.findByTestId("wizard-step-review");
    await user.click(screen.getByTestId("wizard-nav-finish"));

    await screen.findByTestId("wizard-submitting-success");
    expect(screen.getByTestId("wizard-submitting-success")).toHaveAttribute("data-created-status", "channel_pending");
  });
});
