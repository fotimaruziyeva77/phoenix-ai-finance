"use client";

import { useCallback, useState } from "react";

import { useBotKnowledge } from "@/hooks/useBotKnowledge";
import { knowledgeListNeedsPolling } from "@/lib/knowledge-domain/polling";

import { KnowledgeFileList } from "./knowledge-file-list";
import { KnowledgeUploadZone } from "./knowledge-upload-zone";
import styles from "./knowledge.module.css";

export type BotKnowledgePanelProps = {
  botId: string;
  /** When true, uploads are blocked (e.g. archived bot). */
  uploadsDisabled?: boolean;
};

function validateClientPdf(file: File): string | null {
  const name = file.name.trim().toLowerCase();
  if (!name.endsWith(".pdf")) {
    return "Only PDF files are supported. Choose a file that ends with .pdf.";
  }
  const t = (file.type || "").toLowerCase();
  if (t && t !== "application/pdf") {
    return "The file must be a PDF (application/pdf).";
  }
  return null;
}

export function BotKnowledgePanel({ botId, uploadsDisabled }: BotKnowledgePanelProps) {
  const {
    status,
    items,
    total,
    loadError,
    uploadError,
    isUploading,
    refresh,
    upload,
    clearUploadError,
  } = useBotKnowledge(botId);

  const [clientReject, setClientReject] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setClientReject(null);
      clearUploadError();
      const err = validateClientPdf(file);
      if (err) {
        setClientReject(err);
        return;
      }
      await upload(file);
    },
    [upload, clearUploadError],
  );

  const combinedUploadError = clientReject ?? uploadError;
  const dismissUploadError = useCallback(() => {
    setClientReject(null);
    clearUploadError();
  }, [clearUploadError]);

  const polling = knowledgeListNeedsPolling(items);

  return (
    <section className={styles.section} aria-label="Knowledge base" data-testid="bot-knowledge-panel">
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Knowledge base</h3>
          <p className={styles.subtitle}>
            Upload PDFs your bot can search during chats. Processing runs on the server — statuses here reflect real
            pipeline state.
          </p>
        </div>
        <div className={styles.toolbar}>
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={() => void refresh()}
            disabled={status === "loading" || isUploading}
            data-testid="knowledge-refresh-list"
          >
            Refresh list
          </button>
        </div>
      </div>

      {loadError ? (
        <p className={styles.errorBanner} role="alert" data-testid="knowledge-load-error">
          {loadError}
        </p>
      ) : null}

      {uploadsDisabled ? (
        <p className={styles.hint}>Uploads are disabled while this bot is archived.</p>
      ) : (
        <KnowledgeUploadZone
          disabled={uploadsDisabled}
          busy={isUploading}
          onFileSelected={(f) => void handleFile(f)}
          onDismissError={dismissUploadError}
          errorMessage={combinedUploadError}
        />
      )}

      {polling ? (
        <p className={styles.pollingNote} data-testid="knowledge-polling-note">
          Updating automatically while files are queued or processing…
        </p>
      ) : null}

      <KnowledgeFileList items={items} loading={status === "loading"} />

      {status === "success" && total > 0 ? (
        <p className={styles.hint} data-testid="knowledge-total-count">
          {total} file{total === 1 ? "" : "s"} total
        </p>
      ) : null}

      <p className={styles.roadmapNote}>
        Reprocess and delete from the dashboard are not available yet — upload a new file to replace content, or use
        &ldquo;Refresh list&rdquo; after pipeline work completes.
      </p>
    </section>
  );
}
