"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  fetchBotConversation,
  postBotChatTest,
  type BotChatTestResponseDto,
  type ConversationReadDto,
  type MessageReadDto,
} from "@/lib/api/bot-chat-test";
import { ApiError } from "@/lib/api/client";
import { formatAiChatErrorForUser, parseStandardApiError } from "@/lib/api/errors";

export type BotTestChatLastMeta = {
  model_name: string | null;
  latency_ms: number | null;
  tokens_total: number | null;
  cost_usd: string | null;
};

export type UseBotTestChatResult = {
  messages: MessageReadDto[];
  conversationId: string | null;
  /** Latest conversation row from GET transcript; null until a successful load. */
  conversation: ConversationReadDto | null;
  lastMeta: BotTestChatLastMeta | null;
  isLoadingThread: boolean;
  isSending: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  resetThread: () => void;
  refreshThread: () => Promise<void>;
};

function storageKeyForBot(botId: string): string {
  return `bf_bot_test_chat_${botId}`;
}

function metaFromResponse(res: BotChatTestResponseDto): BotTestChatLastMeta {
  return {
    model_name: res.model_name,
    latency_ms: res.latency_ms,
    tokens_total: res.tokens_total,
    cost_usd: res.cost_usd,
  };
}

export function useBotTestChat(botId: string): UseBotTestChatResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const storageKey = useMemo(() => storageKeyForBot(botId), [botId]);

  const [messages, setMessages] = useState<MessageReadDto[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationReadDto | null>(null);
  const [lastMeta, setLastMeta] = useState<BotTestChatLastMeta | null>(null);
  const [isLoadingThread, setIsLoadingThread] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadThread = useCallback(
    async (cid: string, options?: { clearError?: boolean }) => {
      if (!canUseAuthenticatedApi) return;
      const clearError = options?.clearError !== false;
      setIsLoadingThread(true);
      if (clearError) {
        setError(null);
      }
      try {
        const data = await fetchBotConversation(accessToken, botId, cid);
        setMessages(data.messages);
        setConversationId(data.conversation.id);
        setConversation(data.conversation);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setError("Conversation not found. Start a new thread.");
          setMessages([]);
          setConversationId(null);
          setConversation(null);
          try {
            sessionStorage.removeItem(storageKey);
          } catch {
            /* ignore */
          }
        } else {
          setError(formatAiChatErrorForUser(parseStandardApiError(err)));
        }
      } finally {
        setIsLoadingThread(false);
      }
    },
    [accessToken, botId, storageKey, canUseAuthenticatedApi],
  );

  useEffect(() => {
    setMessages([]);
    setLastMeta(null);
    setError(null);
    setConversationId(null);
    setConversation(null);

    if (!hydrated || !canUseAuthenticatedApi) return;

    let stored: string | null = null;
    try {
      stored = sessionStorage.getItem(storageKey);
    } catch {
      stored = null;
    }
    if (stored) {
      setConversationId(stored);
      void loadThread(stored);
    }
  }, [botId, hydrated, accessToken, canUseAuthenticatedApi, storageKey, loadThread]);

  const persistConversationId = useCallback(
    (cid: string | null) => {
      try {
        if (cid) sessionStorage.setItem(storageKey, cid);
        else sessionStorage.removeItem(storageKey);
      } catch {
        /* ignore */
      }
    },
    [storageKey],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !canUseAuthenticatedApi) return;

      setIsSending(true);
      setError(null);
      try {
        const res = await postBotChatTest(accessToken, botId, {
          message: trimmed,
          conversation_id: conversationId,
        });
        setConversationId(res.conversation_id);
        persistConversationId(res.conversation_id);
        setLastMeta(metaFromResponse(res));
        await loadThread(res.conversation_id);
      } catch (err) {
        setError(formatAiChatErrorForUser(parseStandardApiError(err)));
        if (conversationId) {
          await loadThread(conversationId, { clearError: false });
        }
      } finally {
        setIsSending(false);
      }
    },
    [accessToken, botId, conversationId, loadThread, persistConversationId, canUseAuthenticatedApi],
  );

  const resetThread = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setConversation(null);
    setLastMeta(null);
    setError(null);
    persistConversationId(null);
  }, [persistConversationId]);

  const refreshThread = useCallback(async () => {
    if (conversationId) await loadThread(conversationId);
  }, [conversationId, loadThread]);

  return {
    messages,
    conversationId,
    conversation,
    lastMeta,
    isLoadingThread,
    isSending,
    error,
    sendMessage,
    resetThread,
    refreshThread,
  };
}
