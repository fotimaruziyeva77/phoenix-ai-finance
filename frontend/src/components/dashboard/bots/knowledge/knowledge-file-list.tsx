"use client";

import type { KnowledgeFileListItemDto } from "@/lib/api/bot-knowledge";
import { formatDashboardDateTime } from "@/lib/format/datetime";
import { formatFileSizeBytes } from "@/lib/format/filesize";

import { KnowledgeStatusBadge } from "./knowledge-status-badge";
import styles from "./knowledge.module.css";

export type KnowledgeFileListProps = {
  items: KnowledgeFileListItemDto[];
  loading?: boolean;
};

export function KnowledgeFileList({ items, loading }: KnowledgeFileListProps) {
  if (loading && items.length === 0) {
    return <p className={styles.loading}>Loading knowledge files…</p>;
  }

  if (items.length === 0) {
    return (
      <p className={styles.empty} data-testid="knowledge-file-list-empty">
        No knowledge files yet. Upload a PDF to ground your bot in your own documents.
      </p>
    );
  }

  return (
    <ul className={styles.list} aria-label="Knowledge files">
      {items.map((item) => (
        <li key={item.id} className={styles.row} data-testid={`knowledge-file-row-${item.id}`}>
          <div className={styles.fileMain}>
            <p className={styles.fileName}>{item.original_filename}</p>
            <div className={styles.metaRow}>
              <span>{formatFileSizeBytes(item.file_size_bytes)}</span>
              <span>Uploaded {formatDashboardDateTime(item.uploaded_at)}</span>
              {item.page_count != null ? <span>{item.page_count} pages</span> : <span>Pages —</span>}
            </div>
          </div>
          <div className={styles.badgeCell}>
            <KnowledgeStatusBadge status={item.processing_status} />
          </div>
          {item.processing_error ? (
            <p className={styles.errorDetail} data-testid={`knowledge-file-error-${item.id}`}>
              {item.processing_error}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
