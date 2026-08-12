"use client";

import { useCallback, useState } from "react";

import { useLanguage } from "@/contexts/language-context";

import styles from "./faq-section.module.css";

function Chevron() {
  return (
    <svg className={styles.chevron} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FaqItem({ q, a, isOpen, onToggle }: { q: string; a: string; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className={`${styles.item} ${isOpen ? styles.itemOpen : ""}`}>
      <button
        className={styles.summary}
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span>{q}</span>
        <Chevron />
      </button>
      <div className={styles.panelWrap}>
        <div className={styles.panel}>
          <p>{a}</p>
        </div>
      </div>
    </div>
  );
}

export function FaqSection() {
  const { t } = useLanguage();
  const items = t("faq.items") as unknown as Array<{ q: string; a: string }>;
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const toggle = useCallback((i: number) => {
    setOpenIdx((prev) => (prev === i ? null : i));
  }, []);

  return (
    <section id="faq" className="bf-landingSection" aria-labelledby="faq-heading">
      <div className="bf-landingSection__header">
        <h2 id="faq-heading" className="bf-landingSection__title">
          {String(t("faq.title"))}
        </h2>
        <p className="bf-landingSection__lead">{String(t("faq.subtitle"))}</p>
      </div>
      <div className={styles.list} role="region" aria-label="FAQ">
        {Array.isArray(items) && items.map((item, i) => (
          <FaqItem
            key={i}
            q={item.q}
            a={item.a}
            isOpen={openIdx === i}
            onToggle={() => toggle(i)}
          />
        ))}
      </div>
    </section>
  );
}
