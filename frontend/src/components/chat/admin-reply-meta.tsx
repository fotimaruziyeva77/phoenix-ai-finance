"use client";

import type { BotTestChatLastMeta } from "@/hooks/useBotTestChat";

import styles from "./admin-reply-meta.module.css";

function formatUsd(raw: string | null): string | null {
  if (raw == null || raw === "") return null;
  const n = Number(raw);
  if (Number.isNaN(n)) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 8,
  }).format(n);
}

export type AdminReplyMetaProps = {
  meta: BotTestChatLastMeta | null;
};

/** Lightweight admin-only stats for the last successful test reply (omit if nothing to show). */
export function AdminReplyMeta({ meta }: AdminReplyMetaProps) {
  if (!meta) return null;

  const cost = formatUsd(meta.cost_usd);
  const hasAny =
    (meta.model_name && meta.model_name.length > 0) ||
    meta.latency_ms != null ||
    meta.tokens_total != null ||
    cost != null;

  if (!hasAny) return null;

  return (
    <aside className={styles.bar} aria-label="Last reply metrics" data-testid="admin-reply-meta">
      <p className={styles.label}>Last reply</p>
      {meta.model_name ? (
        <span className={styles.chip}>
          <span className={styles.muted}>Model</span> {meta.model_name}
        </span>
      ) : null}
      {meta.tokens_total != null ? (
        <span className={styles.chip}>
          <span className={styles.muted}>Tokens</span> {meta.tokens_total}
        </span>
      ) : null}
      {meta.latency_ms != null ? (
        <span className={styles.chip}>
          <span className={styles.muted}>Latency</span> {meta.latency_ms} ms
        </span>
      ) : null}
      {cost ? (
        <span className={styles.chip}>
          <span className={styles.muted}>Cost</span> {cost}
        </span>
      ) : null}
    </aside>
  );
}
