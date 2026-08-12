import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { BotTestChatPanel } from "./bot-test-chat-panel";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ accessToken: "unit-test-token", hydrated: true }),
}));

vi.mock("@/lib/api/bot-chat-test", () => ({
  postBotChatTest: vi.fn(),
  fetchBotConversation: vi.fn(),
}));

import { fetchBotConversation, postBotChatTest } from "@/lib/api/bot-chat-test";

const convId = "cccccccc-cccc-4ccc-cccc-cccccccccccc";

const baseConversationDto = {
  id: convId,
  bot_id: "bot_unit",
  owner_id: "550e8400-e29b-41d4-a716-446655440000",
  channel: null,
  status: "active",
  current_state: "start",
  detected_intent: null,
  niche_id_snapshot: "education",
  collected_data_json: {},
  last_user_message_at: null,
  last_assistant_message_at: null,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

function mockSuccessfulRoundTrip(userContent: string, assistantContent: string) {
  vi.mocked(postBotChatTest).mockResolvedValue({
    conversation_id: convId,
    user_message_id: "uuuuuuuu-uuuu-4uuu-uuuu-uuuuuuuuuuuu",
    assistant_message_id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    assistant_text: assistantContent,
    model_name: "gemini-test",
    latency_ms: 55,
    tokens_input: 2,
    tokens_output: 4,
    tokens_total: 6,
    cost_usd: "0.000012",
  });

  vi.mocked(fetchBotConversation).mockResolvedValue({
    conversation: {
      ...baseConversationDto,
    },
    messages: [
      {
        id: "uuuuuuuu-uuuu-4uuu-uuuu-uuuuuuuuuuuu",
        conversation_id: convId,
        bot_id: "bot_unit",
        role: "user",
        content: userContent,
        tokens_input: null,
        tokens_output: null,
        tokens_total: null,
        latency_ms: null,
        cost_usd: null,
        model_name: null,
        created_at: "2026-03-01T12:00:01.000Z",
      },
      {
        id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
        conversation_id: convId,
        bot_id: "bot_unit",
        role: "assistant",
        content: assistantContent,
        tokens_input: 2,
        tokens_output: 4,
        tokens_total: 6,
        latency_ms: 55,
        cost_usd: "0.000012",
        model_name: "gemini-test",
        created_at: "2026-03-01T12:00:02.000Z",
      },
    ],
  });
}

describe("BotTestChatPanel", () => {
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

  it("renders test chat chrome without assuming prior messages", async () => {
    const user = userEvent.setup();
    render(<BotTestChatPanel botId="bot_unit" />);
    expect(screen.getByTestId("bot-test-chat-panel")).toBeInTheDocument();
    expect(screen.getByText("Test chat")).toBeInTheDocument();
    expect(screen.getByTestId("chat-message-list-empty")).toBeInTheDocument();
    expect(screen.getByLabelText("Test chat message")).toBeInTheDocument();
    // ChatComposer disables Send until there is non-whitespace input (real behavior, not loading).
    expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
    await user.type(screen.getByLabelText("Test chat message"), "x");
    expect(screen.getByTestId("chat-composer-send")).toBeEnabled();
  });

  it("sends trimmed message and shows transcript from fetchBotConversation (not client-invented text)", async () => {
    const user = userEvent.setup();
    mockSuccessfulRoundTrip("Hello API", "Reply from backend");

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "  Hello API  ");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(postBotChatTest).toHaveBeenCalledWith(
        "unit-test-token",
        "bot_unit",
        expect.objectContaining({ message: "Hello API" }),
      );
    });

    await waitFor(() => {
      expect(fetchBotConversation).toHaveBeenCalledWith("unit-test-token", "bot_unit", convId);
    });

    await waitFor(() => {
      expect(screen.getByText("Hello API")).toBeInTheDocument();
      expect(screen.getByText("Reply from backend")).toBeInTheDocument();
    });
  });

  it("disables composer while request is in flight (loading)", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchBotConversation).mockResolvedValue({
      conversation: { ...baseConversationDto },
      messages: [],
    });

    let releasePost!: (v: Awaited<ReturnType<typeof postBotChatTest>>) => void;
    const postPromise = new Promise<Awaited<ReturnType<typeof postBotChatTest>>>((resolve) => {
      releasePost = resolve;
    });
    vi.mocked(postBotChatTest).mockImplementation(() => postPromise);

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "wait");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
    });
    expect(screen.getByLabelText("Test chat message")).toBeDisabled();

    releasePost({
      conversation_id: convId,
      user_message_id: "u",
      assistant_message_id: "a",
      assistant_text: "done",
      model_name: null,
      latency_ms: null,
      tokens_input: null,
      tokens_output: null,
      tokens_total: null,
      cost_usd: null,
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Test chat message")).not.toBeDisabled();
      expect(screen.getByTestId("chat-composer-send")).toHaveTextContent("Send");
    });
    // Input was cleared on submit; Send stays disabled until the user types again.
    expect(screen.getByTestId("chat-composer-send")).toBeDisabled();
  });

  it("renders API error message cleanly without throwing", async () => {
    const user = userEvent.setup();
    vi.mocked(postBotChatTest).mockRejectedValue(
      new ApiError(
        502,
        JSON.stringify({ error: { code: "ai_inference_failed", message: "Provider unavailable" } }),
      ),
    );

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "x");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-test-chat-error")).toHaveTextContent("Provider unavailable");
    });
  });

  it("shows safe timeout-style error with retry hint (no traceback text)", async () => {
    const user = userEvent.setup();
    const safeMsg = "The AI service took too long to respond. Try again in a moment.";
    vi.mocked(postBotChatTest).mockRejectedValue(
      new ApiError(
        504,
        JSON.stringify({
          error: {
            code: "ai_timeout",
            message: safeMsg,
            category: "ai_chat",
            ai_category: "timeout",
            details: { retryable: true, provider_error_code: "timeout" },
          },
        }),
      ),
    );

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "hello");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      const el = screen.getByTestId("bot-test-chat-error");
      expect(el).toHaveTextContent(safeMsg);
      expect(el).toHaveTextContent("You can try again in a few seconds");
      expect(el.textContent).not.toMatch(/traceback/i);
      expect(el.textContent).not.toMatch(/File "/);
    });
  });

  it("shows auth config error without implying a retry hint when not retryable", async () => {
    const user = userEvent.setup();
    const safeMsg = "AI credentials or configuration are invalid. Check your workspace setup.";
    vi.mocked(postBotChatTest).mockRejectedValue(
      new ApiError(
        502,
        JSON.stringify({
          error: {
            code: "ai_auth_config",
            message: safeMsg,
            category: "ai_chat",
            ai_category: "auth_config",
            details: { retryable: false, provider_error_code: "auth_failed" },
          },
        }),
      ),
    );

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "x");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      const el = screen.getByTestId("bot-test-chat-error");
      expect(el).toHaveTextContent(safeMsg);
      expect(el.textContent).not.toMatch(/You can try again in a few seconds/);
    });
  });

  it("shows admin metadata from the last successful POST response", async () => {
    const user = userEvent.setup();
    mockSuccessfulRoundTrip("q", "a");

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "q");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      const meta = screen.getByTestId("admin-reply-meta");
      expect(meta).toHaveTextContent("gemini-test");
      expect(meta).toHaveTextContent("6");
      expect(meta).toHaveTextContent("55");
    });
  });

  it("shows sales-oriented copy when goalType is sales without inventing thread state", () => {
    vi.mocked(fetchBotConversation).mockResolvedValue({
      conversation: { ...baseConversationDto },
      messages: [],
    });
    render(<BotTestChatPanel botId="bot_unit" goalType="sales" />);
    expect(screen.queryByTestId("bot-test-chat-conversation-snapshot")).not.toBeInTheDocument();
    expect(screen.getByText(/realistic sales thread/i)).toBeInTheDocument();
  });

  it("does not show conversation snapshot until GET transcript returns", () => {
    vi.mocked(fetchBotConversation).mockResolvedValue({
      conversation: { ...baseConversationDto },
      messages: [],
    });
    render(<BotTestChatPanel botId="bot_unit" />);
    expect(screen.queryByTestId("bot-test-chat-conversation-snapshot")).not.toBeInTheDocument();
  });

  it("multi-turn sends conversation_id on second POST and grows transcript only from API", async () => {
    const user = userEvent.setup();
    const postPayloads: Array<{ message: string; conversation_id?: string | null }> = [];

    const u1 = "uu111111-1111-4111-8111-111111111111";
    const a1 = "aa111111-1111-4111-8111-111111111111";
    const u2 = "uu222222-2222-4222-8222-222222222222";
    const a2 = "aa222222-2222-4222-8222-222222222222";

    let fetchRound = 0;
    vi.mocked(fetchBotConversation).mockImplementation(async () => {
      fetchRound += 1;
      if (fetchRound === 1) {
        return {
          conversation: {
            ...baseConversationDto,
            current_state: "start",
            detected_intent: null,
            collected_data_json: {},
          },
          messages: [
            {
              id: u1,
              conversation_id: convId,
              bot_id: "bot_unit",
              role: "user",
              content: "First user",
              tokens_input: null,
              tokens_output: null,
              tokens_total: null,
              latency_ms: null,
              cost_usd: null,
              model_name: null,
              created_at: "2026-03-01T12:00:01.000Z",
            },
            {
              id: a1,
              conversation_id: convId,
              bot_id: "bot_unit",
              role: "assistant",
              content: "First assistant — one question only?",
              tokens_input: 1,
              tokens_output: 2,
              tokens_total: 3,
              latency_ms: 10,
              cost_usd: "0.000001",
              model_name: "gemini-test",
              created_at: "2026-03-01T12:00:02.000Z",
            },
          ],
        };
      }
      return {
        conversation: {
          ...baseConversationDto,
          current_state: "qualification",
          detected_intent: "sales_interest",
          collected_data_json: {
            student_grade: "Grade 9",
            __orch_target_field: "subject",
          },
        },
        messages: [
          {
            id: u1,
            conversation_id: convId,
            bot_id: "bot_unit",
            role: "user",
            content: "First user",
            tokens_input: null,
            tokens_output: null,
            tokens_total: null,
            latency_ms: null,
            cost_usd: null,
            model_name: null,
            created_at: "2026-03-01T12:00:01.000Z",
          },
          {
            id: a1,
            conversation_id: convId,
            bot_id: "bot_unit",
            role: "assistant",
            content: "First assistant — one question only?",
            tokens_input: 1,
            tokens_output: 2,
            tokens_total: 3,
            latency_ms: 10,
            cost_usd: "0.000001",
            model_name: "gemini-test",
            created_at: "2026-03-01T12:00:02.000Z",
          },
          {
            id: u2,
            conversation_id: convId,
            bot_id: "bot_unit",
            role: "user",
            content: "Second user",
            tokens_input: null,
            tokens_output: null,
            tokens_total: null,
            latency_ms: null,
            cost_usd: null,
            model_name: null,
            created_at: "2026-03-01T12:00:03.000Z",
          },
          {
            id: a2,
            conversation_id: convId,
            bot_id: "bot_unit",
            role: "assistant",
            content: "Second assistant — follow-up question?",
            tokens_input: 2,
            tokens_output: 3,
            tokens_total: 5,
            latency_ms: 11,
            cost_usd: "0.000002",
            model_name: "gemini-test",
            created_at: "2026-03-01T12:00:04.000Z",
          },
        ],
      };
    });

    vi.mocked(postBotChatTest).mockImplementation(async (_token, _botId, payload) => {
      postPayloads.push(payload);
      const n = postPayloads.length;
      return {
        conversation_id: convId,
        user_message_id: n === 1 ? u1 : u2,
        assistant_message_id: n === 1 ? a1 : a2,
        assistant_text: n === 1 ? "First assistant — one question only?" : "Second assistant — follow-up question?",
        model_name: "gemini-test",
        latency_ms: 10,
        tokens_input: 1,
        tokens_output: 2,
        tokens_total: 3,
        cost_usd: "0.000001",
      };
    });

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "First user");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(postPayloads).toHaveLength(1);
      expect(postPayloads[0].conversation_id ?? null).toBeNull();
    });

    await waitFor(() => {
      expect(screen.getByText("First assistant — one question only?")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId("bot-test-chat-current-state")).toHaveTextContent("start");
    });

    await user.type(screen.getByLabelText("Test chat message"), "Second user");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(postPayloads).toHaveLength(2);
      expect(postPayloads[1].conversation_id).toBe(convId);
    });

    await waitFor(() => {
      expect(screen.getByText("Second assistant — follow-up question?")).toBeInTheDocument();
    });

    const assistants = screen.getAllByText(/Assistant ·/);
    expect(assistants.length).toBe(2);

    await waitFor(() => {
      expect(screen.getByTestId("bot-test-chat-current-state")).toHaveTextContent("qualification");
      expect(screen.getByTestId("bot-test-chat-detected-intent")).toHaveTextContent("sales_interest");
      const fields = screen.getByTestId("bot-test-chat-collected-fields");
      expect(fields).toHaveTextContent("student grade");
      expect(fields).toHaveTextContent("Grade 9");
      expect(fields.textContent).not.toMatch(/orch|_qp/i);
      const json = screen.getByTestId("bot-test-chat-collected-json").textContent ?? "";
      expect(json).toContain("student_grade");
      expect(json).toContain("Grade 9");
    });
  });

  it("New thread clears snapshot and stops showing stale API state", async () => {
    const user = userEvent.setup();
    mockSuccessfulRoundTrip("one", "reply one");

    render(<BotTestChatPanel botId="bot_unit" />);

    await user.type(screen.getByLabelText("Test chat message"), "one");
    await user.click(screen.getByTestId("chat-composer-send"));

    await waitFor(() => {
      expect(screen.getByTestId("bot-test-chat-conversation-snapshot")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("bot-test-chat-new-thread"));

    expect(screen.queryByTestId("bot-test-chat-conversation-snapshot")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-message-list-empty")).toBeInTheDocument();
  });
});
