"use client";

import { useCallback, useEffect, useId, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import styles from "./superadmin.module.css";

type Props = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: (reason: string | null) => void;
  onCancel: () => void;
};

export function ModerationSuspendDialog({ open, title, description, confirmLabel, onConfirm, onCancel }: Props) {
  const { t } = useLanguage();
  const sm = (key: string) => String(t(`superadmin.moderation.${key}`));
  const labelId = useId();
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  const submit = useCallback(() => {
    const t = reason.trim();
    onConfirm(t.length ? t : null);
  }, [reason, onConfirm]);

  if (!open) return null;

  return (
    <div className={styles.modalOverlay} role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelId}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 className={styles.modalTitle} id={labelId}>
          {title}
        </h2>
        <p className={styles.modalHint}>{description}</p>
        <label htmlFor={`${labelId}-reason`} className={styles.modalFieldLabel}>
          {sm("internalNote")}
        </label>
        <textarea
          id={`${labelId}-reason`}
          className={styles.textarea}
          placeholder={sm("internalNotePlaceholder")}
          maxLength={1024}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className={styles.modalActions}>
          <button type="button" className={styles.btnNeutral} onClick={onCancel}>
            {sm("cancel")}
          </button>
          <button type="button" className={styles.btnDanger} onClick={submit}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
