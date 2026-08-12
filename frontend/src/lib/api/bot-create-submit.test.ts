import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/client")>();
  return {
    ...actual,
    apiFetchWithAuth: vi.fn(),
  };
});

import { apiFetchWithAuth } from "@/lib/api/client";

import { createBotFromWizard, type CreateBotPayload } from "./bot-create";

const PAYLOAD: CreateBotPayload = {
  name: "Campus Bot",
  niche_id: "education",
  goal_type: "support",
  language: "en",
  tone: "friendly",
  welcome_message: "Hello students!",
  short_description: null,
  initial_channel: "web",
};

describe("createBotFromWizard", () => {
  it("posts payload and returns lifecycle snapshot", async () => {
    vi.mocked(apiFetchWithAuth).mockResolvedValueOnce({
      id: "bot_123",
      status: "active",
      primary_channel: "web",
      name: "Campus Bot",
    });
    await expect(createBotFromWizard("token", PAYLOAD)).resolves.toEqual({
      id: "bot_123",
      status: "active",
      primary_channel: "web",
      name: "Campus Bot",
    });
    expect(apiFetchWithAuth).toHaveBeenCalledWith("/api/v1/bots", "token", {
      method: "POST",
      body: PAYLOAD,
    });
  });
});
