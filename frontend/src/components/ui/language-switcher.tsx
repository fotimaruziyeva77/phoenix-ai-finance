"use client";

import { useLanguage } from "@/contexts/language-context";
import type { Lang } from "@/i18n/translations";
import styles from "./language-switcher.module.css";

/* ── SVG flag icons (4×3 ratio, rounded) ── */

function FlagUS() {
  return (
    <svg className={styles.flag} viewBox="0 0 640 480" aria-hidden="true">
      <rect width="640" height="480" fill="#bd3d44" />
      <rect y="37" width="640" height="37" fill="#fff" />
      <rect y="111" width="640" height="37" fill="#fff" />
      <rect y="185" width="640" height="37" fill="#fff" />
      <rect y="259" width="640" height="37" fill="#fff" />
      <rect y="333" width="640" height="37" fill="#fff" />
      <rect y="407" width="640" height="37" fill="#fff" />
      <rect width="260" height="259" fill="#192f5d" />
    </svg>
  );
}

function FlagUZ() {
  return (
    <svg className={styles.flag} viewBox="0 0 640 480" aria-hidden="true">
      <rect width="640" height="160" fill="#1eb53a" />
      <rect y="160" width="640" height="30" fill="#ce1126" />
      <rect y="190" width="640" height="10" fill="#fff" />
      <rect y="200" width="640" height="80" fill="#fff" />
      <rect y="280" width="640" height="10" fill="#fff" />
      <rect y="290" width="640" height="30" fill="#ce1126" />
      <rect y="320" width="640" height="160" fill="#0099b5" />
      <circle cx="140" cy="80" r="40" fill="#fff" />
      <circle cx="155" cy="80" r="33" fill="#1eb53a" />
    </svg>
  );
}

function FlagRU() {
  return (
    <svg className={styles.flag} viewBox="0 0 640 480" aria-hidden="true">
      <rect width="640" height="160" fill="#fff" />
      <rect y="160" width="640" height="160" fill="#0039a6" />
      <rect y="320" width="640" height="160" fill="#d52b1e" />
    </svg>
  );
}

const LANGS: { code: Lang; label: string; Flag: () => React.ReactElement }[] = [
  { code: "en", label: "English", Flag: FlagUS },
  { code: "uz", label: "O'zbekcha", Flag: FlagUZ },
  { code: "ru", label: "Русский", Flag: FlagRU },
];

type Props = {
  /** Render as compact icon-only buttons (default: false) */
  compact?: boolean;
};

export function LanguageSwitcher({ compact = false }: Props) {
  const { lang, setLang } = useLanguage();

  return (
    <div className={styles.wrap} role="group" aria-label="Select language">
      {LANGS.map(({ code, label, Flag }) => (
        <button
          key={code}
          type="button"
          className={`${styles.btn} ${lang === code ? styles.active : ""}`}
          onClick={() => setLang(code)}
          aria-pressed={lang === code}
          aria-label={label}
          title={label}
        >
          <Flag />
          {!compact && <span className={styles.label}>{code.toUpperCase()}</span>}
        </button>
      ))}
    </div>
  );
}
