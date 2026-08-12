import type { KnowledgeProcessingStatus } from "@/lib/api/bot-knowledge";
import { knowledgeStatusDescription, knowledgeStatusLabel, knowledgeStatusVariant } from "@/lib/knowledge-domain/status";

import styles from "./knowledge.module.css";

const variantClass: Record<string, string> = {
  queued: styles.badgeQueued ?? "",
  progress: styles.badgeProgress ?? "",
  ready: styles.badgeReady ?? "",
  failed: styles.badgeFailed ?? "",
};

export function KnowledgeStatusBadge({ status }: { status: KnowledgeProcessingStatus }) {
  const v = knowledgeStatusVariant(status);
  const label = knowledgeStatusLabel(status);
  const title = knowledgeStatusDescription(status);
  return (
    <span className={variantClass[v] ?? styles.badgeQueued} title={title}>
      {label}
    </span>
  );
}
