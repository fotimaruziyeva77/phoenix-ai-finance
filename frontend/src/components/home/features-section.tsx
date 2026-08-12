"use client";

import { useLanguage } from "@/contexts/language-context";

import styles from "./features-section.module.css";

export function FeaturesSection() {
  const { t } = useLanguage();
  const items = t("features.items") as unknown as Array<{ title: string; desc: string }>;

  return (
    <section id="features" className="bf-landingSection" aria-labelledby="features-heading">
      <div className="bf-landingSection__header">
        <h2 id="features-heading" className="bf-landingSection__title">
          {String(t("features.title"))}
        </h2>
        <p className="bf-landingSection__lead">
          {String(t("features.subtitle"))}
        </p>
      </div>
      <ul className={styles.grid}>
        {Array.isArray(items) && items.map((item, i) => (
          <li key={i} className={styles.card}>
            <h3 className={styles.cardTitle}>{item.title}</h3>
            <p className={styles.cardBody}>{item.desc}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
