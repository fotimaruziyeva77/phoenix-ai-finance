"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";

import { HeroChatMock } from "./hero-chat-mock";
import styles from "./hero.module.css";

export function Hero() {
  const { t } = useLanguage();

  return (
    <section className={styles.hero} aria-labelledby="hero-heading">
      <div className={styles.inner}>
        <div className={styles.copy}>
          <div className={styles.badge} aria-label="Product category">
            <span aria-hidden>✨</span> {String(t("hero.badge"))}
          </div>

          <h1 id="hero-heading" className={styles.headline}>
            {String(t("hero.headline"))}{" "}
            <span className={styles.headlineAccent}>{String(t("hero.headlineAccent"))}</span>
          </h1>

          <p className={styles.subtext}>{String(t("hero.subtext"))}</p>

          <div className={styles.ctas}>
            <Link href="/signup" className={styles.btnPrimary}>
              {String(t("hero.cta"))}
            </Link>
            <a
              href="#how-it-works"
              className={styles.btnSecondary}
              onClick={(e) => {
                e.preventDefault();
                document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth", block: "start" });
                window.history.pushState(null, "", "#how-it-works");
              }}
            >
              {String(t("hero.ctaSecondary"))}
            </a>
          </div>

          <div className={styles.stats} aria-label="Platform stats">
            <span>{String(t("stats.bots"))} {String(t("stats.botsLabel"))}</span>
            <span className={styles.statSep} aria-hidden>·</span>
            <span>{String(t("stats.leads"))} {String(t("stats.leadsLabel"))}</span>
            <span className={styles.statSep} aria-hidden>·</span>
            <span>{String(t("stats.uptime"))} {String(t("stats.uptimeLabel"))}</span>
          </div>
        </div>

        <HeroChatMock />
      </div>
    </section>
  );
}
