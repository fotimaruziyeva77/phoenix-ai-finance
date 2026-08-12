import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BotDetailPage } from "./bot-detail-page";

vi.mock("@/components/dashboard/bots/bot-test-chat-panel", () => ({
  BotTestChatPanel: () => <div data-testid="test-chat-stub" />,
}));

const mockSave = vi.fn().mockResolvedValue(undefined);

const mockBot = {
  id: "b1",
  owner_id: "550e8400-e29b-41d4-a716-446655440000",
  name: "Demo Bot",
  niche_id: "education",
  goal_type: "support" as const,
  status: "draft" as const,
  welcome_message: null,
  tone: null,
  language: "en",
  short_description: null,
  provider_name: "gemini",
  model_name: "gemini-2.5-flash",
  temperature: 0.5,
  max_output_tokens: 512,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

vi.mock("@/hooks/useBotDetail", () => ({
  useBotDetail: () => ({
    status: "success" as const,
    bot: mockBot,
    errorMessage: null,
    saveError: null,
    saveSuccess: null,
    isSaving: false,
    isArchiving: false,
    refresh: vi.fn(),
    save: mockSave,
    archive: vi.fn(),
  }),
}));

describe("BotDetailPage AI settings", () => {
  beforeEach(() => {
    mockSave.mockClear();
  });

  it("shows inference provider label and loaded AI fields for the owner", () => {
    render(<BotDetailPage botId="b1" />);
    expect(screen.getByRole("heading", { name: "AI response" })).toBeInTheDocument();
    expect(screen.getByText("Built-in default")).toBeInTheDocument();
    expect(screen.getByTestId("bot-detail-model-name")).toHaveValue("gemini-2.5-flash");
    expect(screen.getByTestId("bot-detail-temperature")).toHaveValue(0.5);
    expect(screen.getByTestId("bot-detail-max-output-tokens")).toHaveValue(512);
  });

  it("includes AI fields in save payload with valid values", async () => {
    const user = userEvent.setup();
    render(<BotDetailPage botId="b1" />);
    await user.clear(screen.getByTestId("bot-detail-model-name"));
    await user.type(screen.getByTestId("bot-detail-model-name"), "gemini-2.5-flash");
    await user.clear(screen.getByTestId("bot-detail-temperature"));
    await user.type(screen.getByTestId("bot-detail-temperature"), "0.8");
    await user.click(screen.getByTestId("bot-detail-save-btn"));
    expect(mockSave).toHaveBeenCalledWith(
      expect.objectContaining({
        model_name: "gemini-2.5-flash",
        temperature: 0.8,
        max_output_tokens: 512,
      }),
    );
  });

  it("rejects out-of-range temperature before calling save", async () => {
    const user = userEvent.setup();
    render(<BotDetailPage botId="b1" />);
    await user.clear(screen.getByTestId("bot-detail-temperature"));
    await user.type(screen.getByTestId("bot-detail-temperature"), "3");
    await user.click(screen.getByTestId("bot-detail-save-btn"));
    expect(mockSave).not.toHaveBeenCalled();
    expect(screen.getByTestId("bot-detail-save-error")).toHaveTextContent(/between 0 and 2/i);
  });
});
