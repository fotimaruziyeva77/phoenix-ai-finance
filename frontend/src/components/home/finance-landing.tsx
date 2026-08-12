"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PhoenixLogo } from "@/components/layout/phoenix-logo";
import {
  IconAdvisor,
  IconChart,
  IconCoins,
  IconGift,
  IconPin,
  IconReceipt,
} from "@/components/ui/icons";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import { calculateCredit } from "@/lib/finance/engine";

import styles from "./finance-landing.module.css";

/**
 * The hero savings figure counts up like a calculator settling on its result —
 * true to how the number is produced (computed live on this page).
 *
 * The state *starts at the target*: server HTML, crawlers, no-JS visitors and
 * hidden tabs (where rAF and timers freeze) all show the real figure. The
 * animation only runs when the page is actually visible and motion is allowed.
 */
function useCountUp(target: number, durationMs = 1400): number {
  const [value, setValue] = useState(target);

  useEffect(() => {
    if (
      document.hidden ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }
    let raf = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - started) / durationMs, 1);
      const eased = 1 - (1 - progress) ** 3;
      setValue(Math.round(target * eased));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return value;
}

/**
 * Phoenix AI landing.
 *
 * The headline savings figure is *computed*, not typed in: the same engine that
 * powers the advisory tools runs at render time, so the number on the marketing
 * page can never drift from the number the product actually shows.
 */

const DEMO_PRINCIPAL_SOM = 200_000_000;
const DEMO_MONTHS = 36;
const MARKET_RATE_PCT = 28; // Hamkorbank, bank.uz 2026-08-12
const BEST_RATE_PCT = 14; // Sanoatqurilishbank, bank.uz 2026-08-12

const PAIN_ICONS = [IconReceipt, IconCoins, IconGift];
const FEAT_ICONS = [IconChart, IconCoins, IconReceipt, IconPin];
const FEAT_HREFS = ["/biznes-reja", "/kredit", "/soliq", "/biznes-reja"];

export function FinanceLanding() {
  const { c, money } = useFinanceLang();
  const l = c.landing;

  const market = calculateCredit({
    principalSom: DEMO_PRINCIPAL_SOM,
    annualRatePct: MARKET_RATE_PCT,
    months: DEMO_MONTHS,
  });
  const best = calculateCredit({
    principalSom: DEMO_PRINCIPAL_SOM,
    annualRatePct: BEST_RATE_PCT,
    months: DEMO_MONTHS,
  });
  const savings = market.totalPaymentSom - best.totalPaymentSom;
  const animatedSavings = useCountUp(savings);

  return (
    <main className="bf-landing">
      <section className={styles.hero}>
        <PhoenixLogo markOnly className={styles.heroPhoenix} />

        <div className={styles.heroContent}>
          <p className={styles.eyebrow}>{l.eyebrow}</p>
          <h1 className={styles.title}>
            {l.titleA} <span className={styles.titleAccent}>{l.titleB}</span>
          </h1>
          <p className={styles.subtitle}>{l.subtitle}</p>

          <div className={styles.ctaRow}>
            <Link href="/maslahatchi" className={styles.ctaPrimary}>
              <IconAdvisor size={16} /> {c.tools.chat}
            </Link>
            <Link href="/biznes-reja" className={styles.ctaSecondary}>
              <IconChart size={16} /> {l.ctaPrimary}
            </Link>
          </div>

          <ul className={styles.trustRow}>
            <li>✓ {l.trustA}</li>
            <li>✓ {l.trustB}</li>
            <li>✓ {l.trustC}</li>
          </ul>

          <div className={styles.statBand}>
            <p className={styles.statLabel}>{l.statLabel}</p>
            <p className={styles.statNumber}>
              {money(animatedSavings)} <span className={styles.statUnit}>{c.currency}</span>
            </p>
            <p className={styles.statCaption}>
              {l.statCaption
                .replace("{amount}", money(DEMO_PRINCIPAL_SOM))
                .replace("{months}", String(DEMO_MONTHS))
                .replace("{best}", String(BEST_RATE_PCT))
                .replace("{market}", String(MARKET_RATE_PCT))}
            </p>
            <p className={styles.statSource}>{l.statSource}</p>
          </div>
        </div>
      </section>

      <section id="muammo" className="bf-landingSection">
        <div className="bf-landingSection__header">
          <h2>{l.painTitle}</h2>
          <p>{l.painSub}</p>
        </div>
        <div className={styles.painGrid}>
          {l.pains.map((p, i) => {
            const Icon = PAIN_ICONS[i]!;
            return (
              <article key={p.title} className={styles.painCard}>
                <div className={styles.painIcon}>
                  <Icon size={26} />
                </div>
                <h3 className={styles.painTitle}>{p.title}</h3>
                <p className={styles.painText}>{p.text}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="features" className="bf-landingSection">
        <div className="bf-landingSection__header">
          <h2>{l.featTitle}</h2>
          <p>{l.featSub}</p>
        </div>
        <div className={styles.grid}>
          {l.feats.map((f, i) => {
            const Icon = FEAT_ICONS[i]!;
            return (
              <Link key={f.title} href={FEAT_HREFS[i]!} className={styles.card}>
                <div className={styles.cardIcon}>
                  <Icon size={24} />
                </div>
                <h3 className={styles.cardTitle}>{f.title}</h3>
                <p className={styles.cardText}>{f.text}</p>
                <span className={styles.cardArrow} aria-hidden>
                  →
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="bf-landingSection">
        <div className="bf-landingSection__header">
          <h2>{l.trustTitle}</h2>
          <p>{l.trustSub}</p>
        </div>
        <div className={styles.contrast}>
          {l.contrast.map((item, i) => (
            <article
              key={item.who}
              className={styles.contrastCard}
              data-us={i === l.contrast.length - 1}
            >
              <p className={styles.contrastWho}>{item.who}</p>
              <p className={styles.contrastSays}>{item.says}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="faq" className="bf-landingSection">
        <div className="bf-landingSection__header">
          <h2>{l.stepsTitle}</h2>
        </div>
        <div className={styles.steps}>
          {l.steps.map((s, i) => (
            <article key={s.title} className={styles.step}>
              <span className={styles.stepNum}>{i + 1}</span>
              <div className={styles.stepBody}>
                <p className={styles.stepTitle}>{s.title}</p>
                <p className={styles.stepText}>{s.text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.finalCta}>
        <h2 className={styles.finalTitle}>{l.finalTitle}</h2>
        <p className={styles.finalText}>{l.finalText}</p>
        <Link href="/maslahatchi" className={styles.ctaPrimary}>
          {l.finalCta}
        </Link>
      </section>

      <p className={styles.disclaimerBand}>{l.disclaimer}</p>
    </main>
  );
}
