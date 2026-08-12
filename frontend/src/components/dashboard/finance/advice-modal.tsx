"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { PhoenixLogo } from "@/components/layout/phoenix-logo";
import { useFinanceLang } from "@/hooks/useFinanceLang";

import styles from "./advice-modal.module.css";

/**
 * "AI maslahati" — one button + one modal, reused under every result card
 * (business plan, credit, tax, and therefore the advisor chat too).
 *
 * Flow: click → modal opens in loading state → the server-side Gemini bridge
 * phrases the ALREADY COMPUTED figures → text streams into the dialog. When the
 * bridge is unavailable the modal says so honestly; the numbers on the page
 * never depend on it.
 */

type Status = "idle" | "loading" | "ready" | "unavailable";

export function AdviceButton({ summary }: { summary: string }) {
  const { c, lang } = useFinanceLang();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [text, setText] = useState("");
  // The summary for one result never changes; cache the answer per mount.
  const fetchedFor = useRef<string | null>(null);

  const request = useCallback(async () => {
    if (fetchedFor.current === summary) return;
    fetchedFor.current = summary;
    setStatus("loading");
    try {
      const res = await fetch("/api/advisor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary, lang }),
      });
      const data = (await res.json()) as { available?: boolean; text?: string };
      if (data.available && data.text) {
        setText(data.text);
        setStatus("ready");
      } else {
        // Don't pin the cache on failure — reopening the modal retries.
        fetchedFor.current = null;
        setStatus("unavailable");
      }
    } catch {
      fetchedFor.current = null;
      setStatus("unavailable");
    }
  }, [summary, lang]);

  const openModal = () => {
    setOpen(true);
    void request();
  };

  return (
    <>
      <button type="button" className={styles.trigger} onClick={openModal}>
        <PhoenixLogo markOnly className={styles.triggerMark} />
        {status === "loading" ? c.ai.loadingButton : c.ai.button}
      </button>
      {open ? (
        <AdviceModal status={status} text={text} onClose={() => setOpen(false)} />
      ) : null}
    </>
  );
}

function AdviceModal({
  status,
  text,
  onClose,
}: {
  status: Status;
  text: string;
  onClose: () => void;
}) {
  const { c } = useFinanceLang();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    // Lock the page scroll while the dialog is up.
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className={styles.overlay} onClick={onClose} role="presentation">
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label={c.ai.title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.head}>
          <span className={styles.headMark}>
            <PhoenixLogo markOnly className={styles.headLogo} />
          </span>
          <div className={styles.headText}>
            <p className={styles.headTitle}>{c.ai.title}</p>
            <p className={styles.headSub}>{c.ai.subtitle}</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label={c.ai.close}
          >
            ✕
          </button>
        </header>

        <div className={styles.body}>
          {status === "loading" || status === "idle" ? (
            <div className={styles.loading} aria-live="polite">
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.loadingText}>{c.ai.loading}</span>
            </div>
          ) : status === "ready" ? (
            <p className={styles.text}>{text}</p>
          ) : (
            <p className={styles.unavailable}>{c.ai.unavailable}</p>
          )}
        </div>

        <footer className={styles.foot}>
          <p className={styles.note}>{c.ai.note}</p>
          <button type="button" className={styles.closeBtn} onClick={onClose}>
            {c.ai.close}
          </button>
        </footer>
      </div>
    </div>
  );
}
