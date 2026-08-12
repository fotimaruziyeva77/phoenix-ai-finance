"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";
import { usePathname } from "next/navigation";

import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { PhoenixLogo } from "@/components/layout/phoenix-logo";
import { TOOL_ICONS } from "@/components/dashboard/finance/tool-shell";
import { useLanguage } from "@/contexts/language-context";
import { useFinanceLang } from "@/hooks/useFinanceLang";
import { useAuth } from "@/hooks/useAuth";

import { MARKETING_NAV_LINKS } from "./nav-config";
import styles from "./marketing-navbar.module.css";

function NavAuthLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { user, hydrated, logout } = useAuth();
  const { t } = useLanguage();

  if (!hydrated) {
    return (
      <span className={styles.navLink} aria-hidden>
        …
      </span>
    );
  }

  if (user) {
    return (
      <>
        <Link href="/dashboard" className={styles.btnGhost} onClick={onNavigate}>
          {String(t("nav.dashboard"))}
        </Link>
        <button type="button" className={styles.btnLogout} onClick={() => { onNavigate?.(); logout(); }}>
          {String(t("nav.logout"))}
        </button>
      </>
    );
  }

  return (
    <>
      <Link href="/login" className={styles.btnGhost} onClick={onNavigate}>
        {String(t("nav.login"))}
      </Link>
      <Link href="/signup" className={styles.btnPrimary} onClick={onNavigate}>
        {String(t("nav.getStarted"))}
      </Link>
    </>
  );
}

export function MarketingNavbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const panelId = useId();
  const pathname = usePathname();

  // Tool labels come from the finance copy so they follow the language switcher.
  const { c } = useFinanceLang();
  const labelFor = (item: (typeof MARKETING_NAV_LINKS)[number]) => {
    const Icon = item.toolKey ? TOOL_ICONS[item.toolKey] : null;
    const text = item.toolKey ? c.tools[item.toolKey] : item.label;
    return Icon ? (
      <>
        <Icon size={14} /> {text}
      </>
    ) : (
      text
    );
  };

  /** Smooth-scroll to a hash target instead of hard-jumping. */
  const handleAnchorClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
      const hash = href.split("#")[1];
      if (!hash) return;

      if (pathname === "/") {
        e.preventDefault();
        const el = document.getElementById(hash);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
          window.history.pushState(null, "", `#${hash}`);
        }
      }
    },
    [pathname],
  );

  // Track scroll to add shadow
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className={`${styles.wrap} ${scrolled ? styles.scrolled : ""}`} role="banner">
      <div className={styles.row}>
        <Link href="/" className={styles.brand} onClick={() => setOpen(false)}>
          <PhoenixLogo showTagline taglineText={c.brandTagline} />
        </Link>

        <nav className={styles.navDesktop} aria-label="Main">
          <div className={styles.navPill}>
            {MARKETING_NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={styles.navLink}
                onClick={(e) => handleAnchorClick(e, item.href)}
              >
                {labelFor(item)}
              </Link>
            ))}
          </div>
          <div className={styles.navAuth}>
            <LanguageSwitcher />
            <div className={styles.authDivider} aria-hidden />
            <NavAuthLinks />
          </div>
        </nav>

        <button
          type="button"
          className={styles.menuBtn}
          aria-expanded={open}
          aria-controls={panelId}
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <span className={styles.srOnly}>{open ? "Close menu" : "Open menu"}</span>
          {open ? <CloseIcon className={styles.menuIcon} /> : <MenuIcon className={styles.menuIcon} />}
        </button>
      </div>

      {open ? (
        <div className={styles.mobilePanel} id={panelId}>
          <nav className={styles.mobileNav} aria-label="Mobile menu">
            {MARKETING_NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={styles.navLink}
                onClick={(e) => {
                  setOpen(false);
                  handleAnchorClick(e, item.href);
                }}
              >
                {labelFor(item)}
              </Link>
            ))}
            <div className={styles.mobileLang}>
              <LanguageSwitcher />
            </div>
            <div className={styles.mobileAuth}>
              <NavAuthLinks onNavigate={() => setOpen(false)} />
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

function MenuIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M6 6l12 12M18 6L6 18"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
