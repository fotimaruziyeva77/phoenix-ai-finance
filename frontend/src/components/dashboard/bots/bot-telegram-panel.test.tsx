import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useBotTelegram } from "@/hooks/useBotTelegram";

import { BotTelegramPanel } from "./bot-telegram-panel";

const mockRefresh = vi.fn().mockResolvedValue(undefined);
const mockConnect = vi.fn().mockResolvedValue(undefined);
const mockDisconnect = vi.fn().mockResolvedValue(undefined);

vi.mock("@/hooks/useBotTelegram", () => ({
  useBotTelegram: vi.fn(),
}));

describe("BotTelegramPanel", () => {
  beforeEach(() => {
    vi.mocked(useBotTelegram).mockReset();
    mockRefresh.mockClear();
    mockConnect.mockClear();
    mockDisconnect.mockClear();
  });

  it("shows load error and retry", async () => {
    vi.mocked(useBotTelegram).mockReturnValue({
      loadStatus: "error",
      status: null,
      loadError: "Could not load Telegram status right now.",
      actionError: null,
      successMessage: null,
      isConnecting: false,
      isDisconnecting: false,
      refresh: mockRefresh,
      connect: mockConnect,
      disconnect: mockDisconnect,
    });

    const user = userEvent.setup();
    render(<BotTelegramPanel botId="b1" />);
    expect(screen.getByTestId("bot-telegram-load-error")).toHaveTextContent(
      "Could not load Telegram status right now.",
    );
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("shows disconnected state and BotFather guidance", () => {
    vi.mocked(useBotTelegram).mockReturnValue({
      loadStatus: "success",
      status: {
        channel_status: "draft",
        configured: false,
        connected: false,
        bot_username: null,
        last_verified_at: null,
        webhook_url_configured: false,
        last_error_code: null,
      },
      loadError: null,
      actionError: null,
      successMessage: null,
      isConnecting: false,
      isDisconnecting: false,
      refresh: mockRefresh,
      connect: mockConnect,
      disconnect: mockDisconnect,
    });

    render(<BotTelegramPanel botId="b1" />);
    expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent("Not started");
    expect(screen.getByTestId("bot-telegram-botfather-note")).toHaveTextContent("BotFather");
    expect(screen.getByTestId("bot-telegram-disconnect")).toBeDisabled();
  });

  it("shows username when API returns it", () => {
    vi.mocked(useBotTelegram).mockReturnValue({
      loadStatus: "success",
      status: {
        channel_status: "active",
        configured: true,
        connected: true,
        bot_username: "my_store_bot",
        last_verified_at: "2026-04-08T12:00:00.000Z",
        webhook_url_configured: true,
        last_error_code: null,
      },
      loadError: null,
      actionError: null,
      successMessage: null,
      isConnecting: false,
      isDisconnecting: false,
      refresh: mockRefresh,
      connect: mockConnect,
      disconnect: mockDisconnect,
    });

    render(<BotTelegramPanel botId="b1" />);
    expect(screen.getByTestId("bot-telegram-status-pill")).toHaveTextContent("Active");
    expect(screen.getByTestId("bot-telegram-username")).toHaveTextContent("@my_store_bot");
    expect(screen.getByTestId("bot-telegram-webhook-hint")).toHaveTextContent("Webhook registered");
  });

  it("disables connect when archived", () => {
    vi.mocked(useBotTelegram).mockReturnValue({
      loadStatus: "success",
      status: {
        channel_status: "active",
        configured: true,
        connected: true,
        bot_username: "x",
        last_verified_at: null,
        webhook_url_configured: false,
        last_error_code: null,
      },
      loadError: null,
      actionError: null,
      successMessage: null,
      isConnecting: false,
      isDisconnecting: false,
      refresh: mockRefresh,
      connect: mockConnect,
      disconnect: mockDisconnect,
    });

    render(<BotTelegramPanel botId="b1" archived />);
    expect(screen.getByTestId("bot-telegram-archived-notice")).toBeInTheDocument();
    expect(screen.getByTestId("bot-telegram-token-input")).toBeDisabled();
    expect(screen.getByTestId("bot-telegram-connect")).toBeDisabled();
  });
});
