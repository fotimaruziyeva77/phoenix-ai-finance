"use client";

import { useCallback, useState } from "react";

import styles from "./chat-composer.module.css";

export type ChatComposerProps = {
  onSend: (text: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  sendLabel?: string;
};

export function ChatComposer({
  onSend,
  disabled = false,
  placeholder = "Type a test message…",
  sendLabel = "Send",
}: ChatComposerProps) {
  const [value, setValue] = useState("");

  const submit = useCallback(async () => {
    const t = value.trim();
    if (!t || disabled) return;
    setValue("");
    await onSend(t);
  }, [value, disabled, onSend]);

  return (
    <div className={styles.wrap} data-testid="chat-composer">
      <div className={styles.row}>
        <textarea
          className={styles.textarea}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          rows={2}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          aria-label="Test chat message"
        />
        <button
          type="button"
          className={styles.sendBtn}
          onClick={() => void submit()}
          disabled={disabled || !value.trim()}
          data-testid="chat-composer-send"
        >
          {sendLabel}
        </button>
      </div>
      <p className={styles.hint}>Enter to send · Shift+Enter for newline</p>
    </div>
  );
}
