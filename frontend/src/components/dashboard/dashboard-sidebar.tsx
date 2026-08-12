"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { CustomerDashboardNavItem } from "@/config/customer-dashboard-nav";

import styles from "./dashboard-sidebar.module.css";

type Props = {
  items: readonly CustomerDashboardNavItem[];
  pathname: string;
  onNavigate?: () => void;
  /** Stable target for e2e (desktop vs mobile duplicate nav). */
  navTestId?: string;
  /** Extra link(s) above the marketing-site footer (e.g. platform admin entry). */
  footerAddon?: ReactNode;
};

function NavIcon({ id }: { id: string }): ReactNode {
  const common = { className: styles.icon, viewBox: "0 0 24 24", fill: "none" as const, "aria-hidden": true };
  switch (id) {
    case "overview":
      return (
        <svg {...common}>
          <path
            d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "bots":
      return (
        <svg {...common}>
          <rect x="5" y="8" width="6" height="10" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <rect x="13" y="5" width="6" height="13" rx="2" stroke="currentColor" strokeWidth="1.75" />
        </svg>
      );
    case "leads":
      return (
        <svg {...common}>
          <path
            d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M12.5 7a4 4 0 1 0-4 4 4 4 0 0 0 4-4Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      );
    case "analytics":
      return (
        <svg {...common}>
          <path d="M4 19V5M9 19V9M14 19v-6M19 19V11" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case "billing":
      return (
        <svg {...common}>
          <rect x="2" y="5" width="20" height="14" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <path d="M2 10h20" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M6 15h4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.75" />
          <path
            d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      );
    default:
      return null;
  }
}

const HREF_TO_ICON: Record<string, string> = {
  "/dashboard": "overview",
  "/dashboard/bots": "bots",
  "/dashboard/leads": "leads",
  "/dashboard/analytics": "analytics",
  "/dashboard/billing": "billing",
  "/dashboard/settings": "settings",
};

export function DashboardSidebar({ items, pathname, onNavigate, navTestId, footerAddon }: Props) {
  return (
    <aside className={styles.aside} aria-label="Workspace">
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden>
          BF
        </span>
        <div className={styles.brandText}>
          <span className={styles.brandName}>BotForge AI</span>
          <span className={styles.brandHint}>Workspace</span>
        </div>
      </div>
      <nav className={styles.nav} aria-label="Primary" data-testid={navTestId}>
        {items.map((item) => {
          const active =
            pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
          const iconId = HREF_TO_ICON[item.href] ?? "overview";
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.link} ${active ? styles.linkActive : ""}`}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
            >
              <NavIcon id={iconId} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className={styles.footer}>
        {footerAddon}
        <Link href="/" className={styles.footerLink} onClick={onNavigate}>
          ← Marketing site
        </Link>
      </div>
    </aside>
  );
}
