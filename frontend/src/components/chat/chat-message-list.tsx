"use client";

import { formatDashboardDateTime } from "@/lib/format/datetime";
import type { MessageReadDto } from "@/lib/api/bot-chat-test";

import styles from "./chat-message-list.module.css";

export type ChatMessageListProps = {
  messages: MessageReadDto[];
  emptyHint: string;
  isLoading?: boolean;
};

function roleLabel(role: string): string {
  if (role === "user") return "You";
  if (role === "assistant") return "Assistant";
  return "System";
}

export function ChatMessageList({ messages, emptyHint, isLoading }: ChatMessageListProps) {
  if (isLoading && messages.length === 0) {
    return (
      <div className={styles.scroll} data-testid="chat-message-list-loading" aria-busy="true">
        <p className={styles.empty}>Loading conversation…</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className={styles.scroll} data-testid="chat-message-list-empty">
        <p className={styles.empty}>{emptyHint}</p>
      </div>
    );
  }

  return (
    <div className={styles.scroll} data-testid="chat-message-list">
      {messages.map((m) => {
        const isUser = m.role === "user";
        const isAssistant = m.role === "assistant";
        return (
          <div
            key={m.id}
            className={`${styles.bubbleRow} ${isUser ? styles.bubbleRowUser : styles.bubbleRowAssistant}`}
          >
            <div>
              <div
                className={`${styles.bubble} ${
                  isUser ? styles.bubbleUser : isAssistant ? styles.bubbleAssistant : styles.bubbleAssistant
                } ${m.role === "system" ? styles.roleSystem : ""}`}
              >
                {m.content}
              </div>
              <div className={styles.bubbleMeta}>
                {roleLabel(m.role)} · {formatDashboardDateTime(m.created_at)}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
