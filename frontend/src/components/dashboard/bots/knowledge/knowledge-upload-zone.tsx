"use client";

import { useCallback, useState } from "react";

import styles from "./knowledge.module.css";

export type KnowledgeUploadZoneProps = {
  disabled?: boolean;
  busy?: boolean;
  onFileSelected: (file: File) => void;
  onDismissError?: () => void;
  errorMessage?: string | null;
};

export function KnowledgeUploadZone({
  disabled,
  busy,
  onFileSelected,
  onDismissError,
  errorMessage,
}: KnowledgeUploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      const file = list.item(0);
      if (!file) return;
      onDismissError?.();
      onFileSelected(file);
    },
    [onDismissError, onFileSelected],
  );

  const zoneClass = [
    styles.dropzone,
    dragOver ? styles.dropzoneDragging : "",
    disabled || busy ? styles.dropzoneDisabled : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={styles.section}>
      {errorMessage ? (
        <p className={styles.errorBanner} role="alert" data-testid="knowledge-upload-error">
          {errorMessage}
        </p>
      ) : null}
      <div
        className={zoneClass}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled && !busy) setDragOver(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !busy) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (disabled || busy) return;
          handleFiles(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept="application/pdf,.pdf"
          className={styles.dropzoneInput}
          disabled={disabled || busy}
          aria-label="Upload PDF knowledge file"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <p className={styles.dropzoneTitle}>{busy ? "Uploading…" : "Drop a PDF here or click to browse"}</p>
        <p className={styles.dropzoneMeta}>
          PDF only · Your file is stored securely and processed server-side. Status updates appear in the list below.
        </p>
      </div>
    </div>
  );
}
