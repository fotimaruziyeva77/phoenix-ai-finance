"use client";

import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { useLanguage } from "@/contexts/language-context";

import styles from "./dashboard-topbar.module.css";

export type DashboardTopbarProps = {
  pageTitle: string;
  productSubtitle?: string;
  userEmail: string;
  userInitial: string;
  onLogout: () => void;
  menuOpen: boolean;
  onMenuToggle: () => void;
  /** Mobile drawer id for ``aria-controls`` (default customer shell). */
  navDrawerId?: string;
};

export function DashboardTopbar({
  pageTitle,
  productSubtitle = "BotForge AI",
  userEmail,
  userInitial,
  onLogout,
  menuOpen,
  onMenuToggle,
  navDrawerId = "dashboard-nav-drawer",
}: DashboardTopbarProps) {
  const { t } = useLanguage();
  return (
    <header className={styles.bar}>
      <div className={styles.left}>
        <button
          type="button"
          className={styles.menuBtn}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          aria-controls={navDrawerId}
          onClick={onMenuToggle}
        >
          <svg className={styles.menuIcon} viewBox="0 0 24 24" fill="none" aria-hidden>
            {menuOpen ? (
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            ) : (
              <path
                d="M4 7h16M4 12h16M4 17h16"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            )}
          </svg>
        </button>
        <div className={styles.titles}>
          <h1 className={styles.title}>{pageTitle}</h1>
          <p className={styles.subtitle}>{productSubtitle}</p>
        </div>
      </div>
      <div className={styles.right}>
        <LanguageSwitcher compact />
        <div className={styles.profileWrap}>
          <button
            type="button"
            className={styles.profileTrigger}
            disabled
            title="Account menu — connect your profile dropdown here"
            aria-label="Account menu (coming soon)"
          >
            <span className={styles.avatar} aria-hidden>
              {userInitial}
            </span>
            <span className={styles.profileLabel}>{userEmail}</span>
          </button>
        </div>
        <button type="button" className={styles.logout} onClick={onLogout}>
          {String(t("dashboard.topbar.logout"))}
        </button>
      </div>
    </header>
  );
}
