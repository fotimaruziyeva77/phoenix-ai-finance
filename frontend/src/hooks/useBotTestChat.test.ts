import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { useBotTestChat } from "./useBotTestChat";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ accessToken: "hook-test-token", hydrated: true }),
}));

vi.mock("@/lib/api/bot-chat-test", () => ({
  postBotChatTest: vi.fn(),
  fetchBotConversation: vi.fn(),
}));

import { fetchBotConversation, postBotChatTest } from "@/lib/api/bot-chat-test";

const convId = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa";

const convDto = {
  id: convId,
  bot_id: "b1",
  owner_id: "550e8400-e29b-41d4-a716-446655440000",
  channel: null,
  status: "active",
  current_state: "qualification",
  detected_intent: "sales_interest",
  niche_id_snapshot: "education",
  collected_data_json: { student_grade: "Grade 9" },
  last_user_message_at: null,
  last_assistant_message_at: null,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

describe("useBotTestChat", () => {
  beforeEach(() => {
    vi.mocked(postBotChatTest).mockReset();
    vi.mocked(fetchBotConversation).mockReset();
    try {
      sessionStorage.clear();
    } catch {
      /* ignore */
    }
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("after a failed send on an existing thread, refetches transcript from the API (no fake state)", async () => {
    vi.mocked(fetchBotConversation).mockResolvedValue({
      conversation: convDto,
      messages: [],
    });

    vi.mocked(postBotChatTest)
      .mockResolvedValueOnce({
        conversation_id: convId,
        user_message_id: "u1",
        assistant_message_id: "a1",
        assistant_text: "ok",
        model_name: "m",
        latency_ms: 1,
        tokens_input: 1,
        tokens_output: 1,
        tokens_total: 2,
        cost_usd: "0",
      })
      .mockRejectedValueOnce(
        new ApiError(
          502,
          JSON.stringify({ error: { code: "ai_inference_failed", message: "Provider down" } }),
        ),
      );

    const { result } = renderHook(() => useBotTestChat("b1"));

    await act(async () => {
      await result.current.sendMessage("first");
    });

    await waitFor(() => {
      expect(result.current.conversationId).toBe(convId);
      expect(result.current.conversation?.current_state).toBe("qualification");
    });

    const loadsAfterFirstSuccess = vi.mocked(fetchBotConversation).mock.calls.length;

    await act(async () => {
      await result.current.sendMessage("second");
    });

    await waitFor(() => {
      expect(result.current.error).toContain("Provider down");
    });

    expect(vi.mocked(fetchBotConversation).mock.calls.length).toBeGreaterThan(loadsAfterFirstSuccess);
    const lastCall = vi.mocked(fetchBotConversation).mock.calls.at(-1);
    expect(lastCall?.[2]).toBe(convId);
    expect(result.current.conversation?.current_state).toBe("qualification");
  });
});
