import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useBotWidget } from "@/hooks/useBotWidget";

import { BotWidgetPanel } from "./bot-widget-panel";

const mockSave = vi.fn().mockResolvedValue(undefined);
const mockRefresh = vi.fn();

const baseConfig = {
  id: "w1",
  bot_id: "b1",
  public_widget_key: "pk_test_123",
  is_enabled: true,
  allowed_domains: ["example.com"],
  theme: null as string | null,
  welcome_text: "Hi there" as string | null,
  widget_settings: null,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

vi.mock("@/hooks/useBotWidget", () => ({
  useBotWidget: vi.fn(),
}));

describe("BotWidgetPanel", () => {
  beforeEach(() => {
    vi.mocked(useBotWidget).mockReset();
    mockSave.mockReset();
    mockSave.mockResolvedValue(undefined);
    mockRefresh.mockReset();
  });

  it("shows load error and retry", async () => {
    vi.mocked(useBotWidget).mockReturnValue({
      loadStatus: "error",
      config: null,
      loadError: "Could not load widget settings right now.",
      saveError: null,
      saveSuccess: null,
      isSaving: false,
      refresh: mockRefresh,
      save: mockSave,
    });

    const user = userEvent.setup();
    render(<BotWidgetPanel botId="b1" />);
    expect(screen.getByTestId("bot-widget-load-error")).toHaveTextContent(
      "Could not load widget settings right now.",
    );
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("renders settings from API and copies embed snippet", async () => {
    vi.mocked(useBotWidget).mockReturnValue({
      loadStatus: "success",
      config: baseConfig,
      loadError: null,
      saveError: null,
      saveSuccess: null,
      isSaving: false,
      refresh: mockRefresh,
      save: mockSave,
    });

    const writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);

    render(<BotWidgetPanel botId="b1" />);

    expect(await screen.findByTestId("bot-widget-public-key")).toHaveTextContent("pk_test_123");
    expect(screen.getByTestId("bot-widget-snippet")).toHaveTextContent("pk_test_123");
    expect(screen.getByTestId("bot-widget-snippet")).toHaveTextContent("BotforgeWidget.init");

    const user = userEvent.setup();
    await user.click(screen.getByTestId("bot-widget-copy-snippet"));
    await waitFor(() => {
      expect(writeTextSpy).toHaveBeenCalledWith(expect.stringContaining("pk_test_123"));
    });
    expect(screen.getByTestId("bot-widget-copy-status")).toHaveTextContent(/copied to clipboard/i);
    writeTextSpy.mockRestore();
  });

  it("submits widget patch payload when saving", async () => {
    vi.mocked(useBotWidget).mockReturnValue({
      loadStatus: "success",
      config: baseConfig,
      loadError: null,
      saveError: null,
      saveSuccess: null,
      isSaving: false,
      refresh: mockRefresh,
      save: mockSave,
    });

    const user = userEvent.setup();
    render(<BotWidgetPanel botId="b1" />);
    await screen.findByTestId("bot-widget-panel");

    await user.click(screen.getByTestId("bot-widget-enabled-switch"));
    await user.clear(screen.getByTestId("bot-widget-domains"));
    await user.type(screen.getByTestId("bot-widget-domains"), "a.com\nb.com");
    await user.selectOptions(screen.getByTestId("bot-widget-theme"), "dark");

    await user.click(screen.getByTestId("bot-widget-save-btn"));
    expect(mockSave).toHaveBeenCalledWith({
      is_enabled: false,
      allowed_domains_json: ["a.com", "b.com"],
      theme: "dark",
      welcome_text: "Hi there",
    });
  });
});
