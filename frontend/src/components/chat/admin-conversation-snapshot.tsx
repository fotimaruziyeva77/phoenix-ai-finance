"use client";

import type { ConversationReadDto } from "@/lib/api/bot-chat-test";

import styles from "./admin-conversation-snapshot.module.css";

export type AdminConversationSnapshotProps = {
  conversation: ConversationReadDto | null;
  /** When true, copy and layout emphasize live sales simulation (same API data). */
  salesBot?: boolean;
};

function partitionCollected(raw: Record<string, unknown> | undefined) {
  const owner: Record<string, unknown> = {};
  const technical: Record<string, unknown> = {};
  if (!raw || typeof raw !== "object") {
    return { owner, technical };
  }
  for (const [k, v] of Object.entries(raw)) {
    if (k.startsWith("_")) {
      technical[k] = v;
    } else {
      owner[k] = v;
    }
  }
  return { owner, technical };
}

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Read-only sales-flow snapshot from GET /conversations/{id} — no client-side inference.
 */
export function AdminConversationSnapshot({ conversation, salesBot }: AdminConversationSnapshotProps) {
  if (!conversation) return null;

  const { owner, technical } = partitionCollected(conversation.collected_data_json);
  const hasTechnical = Object.keys(technical).length > 0;
  const fullJson = JSON.stringify(conversation.collected_data_json ?? {}, null, 2);

  return (
    <aside
      className={styles.wrap}
      aria-label="Conversation state from API"
      data-testid="bot-test-chat-conversation-snapshot"
    >
      <p className={styles.label}>{salesBot ? "Sales flow" : "Conversation"}</p>
      <p className={styles.hint}>
        {salesBot
          ? "Live engine: each send runs qualification, state, and one focused reply from your model. Values below are from the server."
          : "Server-owned thread metadata from the transcript endpoint after each send."}
      </p>
      <dl className={styles.grid}>
        <dt className={styles.dt}>State</dt>
        <dd className={styles.dd} data-testid="bot-test-chat-current-state">
          {conversation.current_state}
        </dd>
        <dt className={styles.dt}>Intent</dt>
        <dd className={styles.dd} data-testid="bot-test-chat-detected-intent">
          {conversation.detected_intent ?? "—"}
        </dd>
      </dl>

      <p className={styles.subLabel}>Captured fields</p>
      {Object.keys(owner).length === 0 ? (
        <p className={styles.emptyFields} data-testid="bot-test-chat-collected-empty">
          No qualification fields stored yet.
        </p>
      ) : (
        <ul className={styles.fieldList} data-testid="bot-test-chat-collected-fields">
          {Object.entries(owner).map(([key, val]) => (
            <li key={key} className={styles.fieldRow}>
              <span className={styles.fieldKey}>{key.replace(/_/g, " ")}</span>
              <span className={styles.fieldVal}>{formatFieldValue(val)}</span>
            </li>
          ))}
        </ul>
      )}

      {hasTechnical ? (
        <details className={styles.advanced}>
          <summary className={styles.summary}>Orchestration keys (advanced)</summary>
          <pre className={styles.preMuted} data-testid="bot-test-chat-collected-technical">
            {JSON.stringify(technical, null, 2)}
          </pre>
        </details>
      ) : null}

      <details className={styles.advanced}>
        <summary className={styles.summary}>Full JSON payload</summary>
        <pre className={styles.pre} data-testid="bot-test-chat-collected-json">
          {fullJson}
        </pre>
      </details>
    </aside>
  );
}
