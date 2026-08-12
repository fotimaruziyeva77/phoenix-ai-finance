"use client";

import { AdminConversationSnapshot } from "@/components/chat/admin-conversation-snapshot";
import { AdminReplyMeta } from "@/components/chat/admin-reply-meta";
import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { useBotTestChat } from "@/hooks/useBotTestChat";

import styles from "./bot-test-chat-panel.module.css";

export type BotTestChatPanelProps = {
  botId: string;
  /** Bot goal from detail load — drives copy only; chat still uses the real API. */
  goalType?: string | null;
};

/**
 * Dashboard-only test harness: talks to real POST/GET chat APIs.
 * Chat primitives live under `@/components/chat/*` for future embed/widget reuse.
 */
export function BotTestChatPanel({ botId, goalType }: BotTestChatPanelProps) {
  const {
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
  } = useBotTestChat(botId);

  const busy = isSending || isLoadingThread;
  const salesBot = (goalType ?? "").trim().toLowerCase() === "sales";

  return (
    <section className={styles.section} aria-label="Test chat" data-testid="bot-test-chat-panel">
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Test chat</h3>
          <p className={styles.subtitle}>
            {salesBot
              ? "Run a realistic sales thread against your live model and niche flow. The transcript, funnel state, and captured fields all come from the server after each message."
              : "Send real messages through your bot configuration. Transcript and metrics come from the API — nothing is simulated in the browser."}
          </p>
        </div>
        <div className={styles.toolbar}>
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={() => void refreshThread()}
            disabled={!conversationId || busy}
            data-testid="bot-test-chat-refresh"
          >
            Refresh
          </button>
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={resetThread}
            disabled={busy}
            data-testid="bot-test-chat-new-thread"
          >
            New thread
          </button>
        </div>
      </div>

      {conversationId ? (
        <p className={styles.threadId} data-testid="bot-test-chat-conversation-id">
          Thread: {conversationId}
        </p>
      ) : null}

      {error ? (
        <p className={styles.errorBanner} role="alert" data-testid="bot-test-chat-error">
          {error}
        </p>
      ) : null}

      <AdminConversationSnapshot conversation={conversation} salesBot={salesBot} />

      <AdminReplyMeta meta={lastMeta} />

      <ChatMessageList
        messages={messages}
        emptyHint="No messages yet. Send one below to run a live test against the model."
        isLoading={isLoadingThread && !isSending}
      />

      <ChatComposer onSend={(t) => void sendMessage(t)} disabled={busy} sendLabel={isSending ? "Sending…" : "Send"} />
    </section>
  );
}
