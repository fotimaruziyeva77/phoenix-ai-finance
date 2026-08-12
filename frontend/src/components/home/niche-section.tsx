"use client";

import { NicheIconByKey } from "@/components/niche/niche-icon-by-key";
import { useLanguage } from "@/contexts/language-context";
import { useNicheCatalog } from "@/contexts/niche-catalog-context";

import styles from "./niche-section.module.css";

export function NicheSection() {
  const { status, niches } = useNicheCatalog();
  const { t } = useLanguage();

  return (
    <section id="niches" className="bf-landingSection" aria-labelledby="niches-heading">
      <div className="bf-landingSection__header">
        <h2 id="niches-heading" className="bf-landingSection__title">
          {String(t("niches.title"))}
        </h2>
        <p className="bf-landingSection__lead">
          {String(t("niches.subtitle"))}
        </p>
      </div>
      {status === "loading" || status === "idle" ? (
        <p className="bf-landingSection__lead" data-testid="landing-niches-loading" aria-busy="true">
          {String(t("niches.loading"))}
        </p>
      ) : (
        <ul className={styles.grid}>
          {niches.map((niche) => (
            <li key={niche.id} className={styles.card}>
              <div className={styles.iconWrap}>
                <NicheIconByKey iconKey={niche.icon_key} />
              </div>
              <h3 className={styles.cardTitle}>{niche.display_name}</h3>
              <p className={styles.cardBody}>{niche.description}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
