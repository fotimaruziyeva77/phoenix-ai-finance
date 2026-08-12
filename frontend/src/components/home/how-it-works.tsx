"use client";

import type { ReactNode } from "react";

import { useLanguage } from "@/contexts/language-context";

import styles from "./how-it-works.module.css";

/* ── Gradient defs shared by all icons ── */
function IconDefs() {
  return (
    <defs>
      <linearGradient id="iconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#a78bfa" />
        <stop offset="100%" stopColor="#60a5fa" />
      </linearGradient>
      <linearGradient id="iconGradSoft" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.5" />
        <stop offset="100%" stopColor="#60a5fa" stopOpacity="0.5" />
      </linearGradient>
    </defs>
  );
}

function IconSignUp() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <IconDefs />
      <circle cx="9" cy="7" r="4" stroke="url(#iconGrad)" strokeWidth="1.75" />
      <path
        d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"
        stroke="url(#iconGrad)"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      <circle cx="19" cy="11" r="3.5" stroke="url(#iconGradSoft)" strokeWidth="1" strokeDasharray="2 2" />
      <path d="M19 9v4M17 11h4" stroke="url(#iconGrad)" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}

function IconNiche() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <IconDefs />
      <circle cx="12" cy="12" r="9" stroke="url(#iconGradSoft)" strokeWidth="1.25" />
      <circle cx="12" cy="12" r="5.5" stroke="url(#iconGrad)" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="2" fill="url(#iconGrad)" />
      <path
        d="M12 3v3M12 18v3M3 12h3M18 12h3"
        stroke="url(#iconGrad)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <IconDefs />
      <rect x="4" y="14" width="16" height="7" rx="2" stroke="url(#iconGradSoft)" strokeWidth="1.25" />
      <circle cx="16" cy="17.5" r="1" fill="url(#iconGrad)" />
      <path
        d="M12 12V4m0 0l3.5 3.5M12 4L8.5 7.5"
        stroke="url(#iconGrad)"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconConnect() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <IconDefs />
      <rect x="1" y="5" width="8" height="6" rx="1.5" stroke="url(#iconGrad)" strokeWidth="1.5" />
      <rect x="15" y="13" width="8" height="6" rx="1.5" stroke="url(#iconGrad)" strokeWidth="1.5" />
      <path
        d="M9 8h2a3 3 0 0 1 3 3v5"
        stroke="url(#iconGrad)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="3 2"
      />
      <circle cx="14" cy="16" r="0" fill="url(#iconGrad)">
        <animate attributeName="r" values="0;1.2;0" dur="2s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function IconLeads() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden>
      <IconDefs />
      <rect x="2" y="3" width="20" height="18" rx="3" stroke="url(#iconGradSoft)" strokeWidth="1.25" />
      <path
        d="M6 15l4-4 3 3 5-5"
        stroke="url(#iconGrad)"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M14 9h4v4" stroke="url(#iconGrad)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const STEP_ICONS: ReactNode[] = [
  <IconSignUp key="signup" />,
  <IconNiche key="niche" />,
  <IconUpload key="upload" />,
  <IconConnect key="connect" />,
  <IconLeads key="leads" />,
];

export function HowItWorks() {
  const { t } = useLanguage();
  const steps = t("howItWorks.steps") as unknown as Array<{ title: string; desc: string }>;

  return (
    <section id="how-it-works" className="bf-landingSection" aria-labelledby="how-heading">
      <div className="bf-landingSection__header">
        <h2 id="how-heading" className="bf-landingSection__title">
          {String(t("howItWorks.title"))}
        </h2>
        <p className="bf-landingSection__lead">
          {String(t("howItWorks.subtitle"))}
        </p>
      </div>
      <ol className={styles.grid}>
        {Array.isArray(steps) && steps.map((step, i) => (
          <li key={i} className={styles.card}>
            <span className={styles.stepNum} aria-hidden>
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className={styles.iconWrap}>{STEP_ICONS[i]}</div>
            <h3 className={styles.cardTitle}>{step.title}</h3>
            <p className={styles.cardBody}>{step.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
