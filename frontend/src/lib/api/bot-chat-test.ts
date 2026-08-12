import { apiFetchWithAuth } from "@/lib/api/client";

/** POST /api/v1/bots/{bot_id}/chat/test — snake_case JSON from FastAPI. */
export type BotChatTestResponseDto = {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  assistant_text: string;
  model_name: string | null;
  latency_ms: number | null;
  tokens_input: number | null;
  tokens_output: number | null;
  tokens_total: number | null;
  /** Decimal serialized as string in JSON */
  cost_usd: string | null;
};

export type ConversationReadDto = {
  id: string;
  bot_id: string;
  owner_id: string;
  channel: string | null;
  status: string;
  /** Sales-flow state machine position (e.g. start, qualification). */
  current_state: string;
  detected_intent: string | null;
  niche_id_snapshot: string | null;
  collected_data_json: Record<string, unknown>;
  last_user_message_at: string | null;
  last_assistant_message_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MessageReadDto = {
  id: string;
  conversation_id: string;
  bot_id: string;
  role: string;
  content: string;
  tokens_input: number | null;
  tokens_output: number | null;
  tokens_total: number | null;
  latency_ms: number | null;
  cost_usd: string | null;
  model_name: string | null;
  created_at: string;
};

export type ConversationMessagesResponseDto = {
  conversation: ConversationReadDto;
  messages: MessageReadDto[];
};

export async function postBotChatTest(
  accessToken: string | null,
  botId: string,
  payload: { message: string; conversation_id?: string | null },
): Promise<BotChatTestResponseDto> {
  const body: Record<string, unknown> = { message: payload.message };
  if (payload.conversation_id) {
    body.conversation_id = payload.conversation_id;
  }
  return apiFetchWithAuth<BotChatTestResponseDto>(`/api/v1/bots/${botId}/chat/test`, accessToken, {
    method: "POST",
    body,
  });
}

export async function fetchBotConversation(
  accessToken: string | null,
  botId: string,
  conversationId: string,
): Promise<ConversationMessagesResponseDto> {
  return apiFetchWithAuth<ConversationMessagesResponseDto>(
    `/api/v1/bots/${botId}/conversations/${conversationId}`,
    accessToken,
    { method: "GET" },
  );
}
