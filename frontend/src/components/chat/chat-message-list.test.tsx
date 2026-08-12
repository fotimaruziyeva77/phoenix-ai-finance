import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { MessageReadDto } from "@/lib/api/bot-chat-test";

import { ChatMessageList } from "./chat-message-list";

const baseMsg = (overrides: Partial<MessageReadDto>): MessageReadDto => ({
  id: "m1",
  conversation_id: "c1",
  bot_id: "b1",
  role: "user",
  content: "Hello",
  tokens_input: null,
  tokens_output: null,
  tokens_total: null,
  latency_ms: null,
  cost_usd: null,
  model_name: null,
  created_at: "2026-03-01T12:00:00.000Z",
  ...overrides,
});

describe("ChatMessageList", () => {
  it("renders empty state with hint when there are no messages", () => {
    render(
      <ChatMessageList messages={[]} emptyHint="Start by sending a message." isLoading={false} />,
    );
    expect(screen.getByTestId("chat-message-list-empty")).toBeInTheDocument();
    expect(screen.getByText("Start by sending a message.")).toBeInTheDocument();
  });

  it("renders loading placeholder when loading and no messages yet", () => {
    render(<ChatMessageList messages={[]} emptyHint="x" isLoading />);
    expect(screen.getByTestId("chat-message-list-loading")).toBeInTheDocument();
    expect(screen.getByText("Loading conversation…")).toBeInTheDocument();
  });

  it("renders user and assistant bubbles from API-shaped messages", () => {
    const messages: MessageReadDto[] = [
      baseMsg({ id: "u1", role: "user", content: "Hi bot" }),
      baseMsg({
        id: "a1",
        role: "assistant",
        content: "Hi there",
        model_name: "flash",
        tokens_total: 5,
      }),
    ];
    render(<ChatMessageList messages={messages} emptyHint="x" />);
    expect(screen.getByTestId("chat-message-list")).toBeInTheDocument();
    expect(screen.getByText("Hi bot")).toBeInTheDocument();
    expect(screen.getByText("Hi there")).toBeInTheDocument();
    expect(screen.getByText(/You ·/)).toBeInTheDocument();
    expect(screen.getByText(/Assistant ·/)).toBeInTheDocument();
  });
});
