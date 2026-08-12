import { afterEach, describe, expect, it, vi } from "vitest";

import { postBotChatTest } from "./bot-chat-test";

describe("postBotChatTest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs message without conversation_id when omitted", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          conversation_id: "c1",
          user_message_id: "u1",
          assistant_message_id: "a1",
          assistant_text: "hi",
          model_name: "m",
          latency_ms: 1,
          tokens_input: 1,
          tokens_output: 1,
          tokens_total: 2,
          cost_usd: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    await postBotChatTest("tok", "bot-1", { message: "hello" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(init.body as string)).toEqual({ message: "hello" });
  });
});
