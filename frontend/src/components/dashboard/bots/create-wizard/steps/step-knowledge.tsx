import { useCallback, useRef, useState } from "react";

import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  updateDraft: (fn: (d: CreateBotDraft) => CreateBotDraft) => void;
  t: TFn;
  pendingFiles: File[];
  onAddFile: (file: File) => { ok: boolean; reason: "not_pdf" | "too_large" | null };
  onRemoveFile: (index: number) => void;
};

/** Format bytes → human-readable size */
function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function StepKnowledge({ draft, updateDraft, t, pendingFiles, onAddFile, onRemoveFile }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(
    (list: FileList | null) => {
      if (!list) return;
      setFileError(null);
      for (let i = 0; i < list.length; i++) {
        const file = list.item(i);
        if (!file) continue;
        const result = onAddFile(file);
        if (!result.ok) {
          if (result.reason === "too_large") {
            setFileError(t("dashboard.wizard.fileTooLarge") as string);
          } else if (result.reason === "not_pdf") {
            setFileError(t("dashboard.wizard.fileNotPdf") as string);
          }
        }
      }
    },
    [onAddFile, t],
  );

  return (
    <>
      <p className={styles.hintBox}>
        {t("dashboard.wizard.knowledgeHint") as string}
      </p>

      <div className={styles.knowledgeList} data-testid="knowledge-source-types">
        <p className={styles.fieldLabel}>{t("dashboard.wizard.typicalSources") as string}</p>
        <ul className={styles.knowledgeBullets}>
          <li>{t("dashboard.wizard.srcPdf") as string}</li>
          <li>{t("dashboard.wizard.srcFaq") as string}</li>
          <li>{t("dashboard.wizard.srcService") as string}</li>
          <li>{t("dashboard.wizard.srcPricing") as string}</li>
        </ul>
      </div>

      {/* ── Upload zone ─────────────────────────────────── */}
      {fileError && (
        <p className={styles.fileError} role="alert" data-testid="knowledge-file-error">
          {fileError}
        </p>
      )}

      <div
        className={[styles.uploadZone, dragOver ? styles.uploadZoneDragging : ""].join(" ")}
        data-testid="knowledge-upload-zone"
        onDragEnter={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          processFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className={styles.uploadZoneInput}
          tabIndex={-1}
          onChange={(e) => {
            processFiles(e.target.files);
            e.target.value = "";
          }}
        />
        {/* Upload icon */}
        <svg className={styles.uploadZoneIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p className={styles.uploadZoneTitle}>
          {t("dashboard.wizard.uploadDropTitle") as string}
        </p>
        <p className={styles.uploadZoneMeta}>
          {t("dashboard.wizard.uploadDropMeta") as string}
        </p>
      </div>

      {/* ── Selected files list ─────────────────────────── */}
      {pendingFiles.length > 0 && (
        <div className={styles.fileList} data-testid="knowledge-pending-files">
          <p className={styles.pendingNote}>
            {t("dashboard.wizard.pendingUploadNote") as string}
          </p>
          {pendingFiles.map((file, idx) => (
            <div className={styles.fileItem} key={`${file.name}-${idx}`}>
              {/* PDF icon */}
              <svg className={styles.fileIcon} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              <div className={styles.fileInfo}>
                <span className={styles.fileName}>{file.name}</span>
                <span className={styles.fileSize}>{fmtSize(file.size)}</span>
              </div>
              <button
                type="button"
                className={styles.fileRemoveBtn}
                onClick={() => onRemoveFile(idx)}
                aria-label={`${t("dashboard.wizard.removeFile") as string} ${file.name}`}
              >
                {t("dashboard.wizard.removeFile") as string}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Notes ───────────────────────────────────────── */}
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel} htmlFor="knowledge-notes">
          {t("dashboard.wizard.notesLabel") as string} <span className={styles.optionalTag}>({t("dashboard.wizard.optional") as string})</span>
        </label>
        <p className={styles.fieldHelp}>{t("dashboard.wizard.notesHelp") as string}</p>
        <textarea
          id="knowledge-notes"
          className={styles.textArea}
          placeholder={t("dashboard.wizard.notesPlaceholder") as string}
          value={draft.knowledge.notes}
          onChange={(e) =>
            updateDraft((d) => ({
              ...d,
              knowledge: { ...d.knowledge, skipped: false, notes: e.target.value },
            }))
          }
        />
      </div>
    </>
  );
}
