"use client";

import Link from "next/link";
import { useCallback } from "react";
import { usePathname } from "next/navigation";

import { useLanguage } from "@/contexts/language-context";

import styles from "./site-footer.module.css";

export function SiteFooter() {
  const year = new Date().getFullYear();
  const { t } = useLanguage();
  const pathname = usePathname();

  const smoothScroll = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, hash: string) => {
      if (pathname === "/") {
        e.preventDefault();
        document.getElementById(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
        window.history.pushState(null, "", `#${hash}`);
      }
    },
    [pathname],
  );

  return (
    <footer className={styles.footer}>
      {/* Gradient accent line */}
      <div className={styles.accentLine} aria-hidden />

      <div className={styles.inner}>
        {/* Brand column */}
        <div className={styles.brandCol}>
          <div className={styles.brandRow}>
            <div className={styles.logoIcon} aria-hidden>
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="4" stroke="url(#footerGrad)" strokeWidth="1.5" />
                <circle cx="9" cy="10" r="1.5" fill="url(#footerGrad)" />
                <circle cx="15" cy="10" r="1.5" fill="url(#footerGrad)" />
                <path d="M8.5 15c.8 1.2 2 1.8 3.5 1.8s2.7-.6 3.5-1.8" stroke="url(#footerGrad)" strokeWidth="1.5" strokeLinecap="round" />
                <defs>
                  <linearGradient id="footerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#a78bfa" />
                    <stop offset="100%" stopColor="#60a5fa" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <p className={styles.brand}>Phoenix AI</p>
          </div>
          <p className={styles.tagline}>{String(t("footer.tagline"))}</p>

          {/* Social links */}
          <div className={styles.socials}>
            <a
              href="mailto:info@phoenix-ai.uz"
              className={styles.socialLink}
              aria-label="Email"
            >
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="2" y="4" width="20" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
                <path d="M2 7l10 7 10-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </a>
            <a
              href="https://t.me/phoenixai_uz"
              className={styles.socialLink}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Telegram"
            >
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M21 3L1 11l7 2.5m13-10.5l-7.5 14L8 13.5m13-10.5L8 13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
          </div>
        </div>

        {/* Product column */}
        <div className={styles.linkCol}>
          <h4 className={styles.colTitle}>{String(t("footer.product"))}</h4>
          <Link href="/#features" className={styles.navLink} onClick={(e) => smoothScroll(e, "features")}>
            {String(t("nav.features"))}
          </Link>
          <Link href="/#pricing" className={styles.navLink} onClick={(e) => smoothScroll(e, "pricing")}>
            {String(t("nav.pricing"))}
          </Link>
          <Link href="/#faq" className={styles.navLink} onClick={(e) => smoothScroll(e, "faq")}>
            {String(t("nav.faq"))}
          </Link>
        </div>

        {/* Legal column */}
        <div className={styles.linkCol}>
          <h4 className={styles.colTitle}>{String(t("footer.legal"))}</h4>
          <Link href="/terms" className={styles.navLink}>
            {String(t("footer.terms"))}
          </Link>
          <Link href="/privacy" className={styles.navLink}>
            {String(t("footer.privacy"))}
          </Link>
        </div>

        {/* Contact column */}
        <div className={styles.linkCol}>
          <h4 className={styles.colTitle}>{String(t("footer.contact"))}</h4>
          <a className={styles.navLink} href="mailto:info@phoenix-ai.uz">
            info@phoenix-ai.uz
          </a>
          <a
            className={styles.navLink}
            href="https://t.me/phoenixai_uz"
            target="_blank"
            rel="noopener noreferrer"
          >
            @phoenixai_uz
          </a>
        </div>
      </div>

      {/* Bottom bar */}
      <div className={styles.bottom}>
        <div className={styles.bottomInner}>
          <span>&copy; {year} Phoenix AI. {String(t("footer.rights"))}</span>
        </div>
      </div>
    </footer>
  );
}
