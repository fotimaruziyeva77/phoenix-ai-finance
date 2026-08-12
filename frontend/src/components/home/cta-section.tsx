"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import styles from "./cta-section.module.css";

export function CtaSection() {
  const { t } = useLanguage();

  return (
    <section className={`bf-landingSection ${styles.wrap}`} aria-labelledby="cta-heading">
      <div className={styles.inner}>
        <h2 id="cta-heading" className={styles.title}>
          {String(t("cta.title"))}
        </h2>
        <p className={styles.subtitle}>{String(t("cta.subtitle"))}</p>
        <Link href="/signup" className={styles.btn}>
          {String(t("cta.button"))} →
        </Link>
      </div>
    </section>
  );
}
