"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { SuperadminNavItem } from "@/config/superadmin-nav";

import styles from "@/components/dashboard/dashboard-sidebar.module.css";

type Props = {
  items: readonly SuperadminNavItem[];
  pathname: string;
  onNavigate?: () => void;
  navTestId?: string;
};

function NavIcon({ id }: { id: string }): ReactNode {
  const common = { className: styles.icon, viewBox: "0 0 24 24", fill: "none" as const, "aria-hidden": true };
  switch (id) {
    case "overview":
      return (
        <svg {...common}>
          <path
            d="M4 14.5V20h5v-7H4v1.5ZM15 4v16h5V4h-5ZM10 9v11h5V9h-5Z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </svg>
      );
    case "users":
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
    case "bots":
      return (
        <svg {...common}>
          <rect x="5" y="8" width="6" height="10" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <rect x="13" y="5" width="6" height="13" rx="2" stroke="currentColor" strokeWidth="1.75" />
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
    case "aiUsage":
      return (
        <svg {...common}>
          <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.2 6L12 22l-3.8-7A7 7 0 0 1 12 2Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
          <circle cx="12" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.75" />
        </svg>
      );
    case "auditLog":
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
          <path d="M14 2v6h6" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
          <path d="M16 13H8M16 17H8M10 9H8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case "featureFlags":
      return (
        <svg {...common}>
          <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
          <path d="M4 22v-7" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case "support":
      return (
        <svg {...common}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
        </svg>
      );
    case "coupons":
      return (
        <svg {...common}>
          <path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6M12 2v20" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M20 6l-3.5 3.5M20 6h-4M20 6v4M4 6l3.5 3.5M4 6h4M4 6v4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "analytics":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.75" />
          <path d="M12 2a10 10 0 0 1 10 10h-10Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" fill="currentColor" fillOpacity="0.15" />
        </svg>
      );
    case "abuse":
      return (
        <svg {...common}>
          <path d="M12 9v4M12 17h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
        </svg>
      );
    case "export":
      return (
        <svg {...common}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M12 15V3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    case "campaigns":
      return (
        <svg {...common}>
          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2Z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
          <path d="M22 6l-10 7L2 6" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
        </svg>
      );
    case "webhookLogs":
      return (
        <svg {...common}>
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      );
    default:
      return null;
  }
}

const HREF_TO_ICON: Record<string, string> = {
  "/superadmin": "overview",
  "/superadmin/users": "users",
  "/superadmin/bots": "bots",
  "/superadmin/billing": "billing",
  "/superadmin/ai-usage": "aiUsage",
  "/superadmin/audit-log": "auditLog",
  "/superadmin/feature-flags": "featureFlags",
  "/superadmin/support": "support",
  "/superadmin/coupons": "coupons",
  "/superadmin/analytics": "analytics",
  "/superadmin/abuse": "abuse",
  "/superadmin/export": "export",
  "/superadmin/campaigns": "campaigns",
  "/superadmin/webhook-logs": "webhookLogs",
};

export function SuperadminSidebar({ items, pathname, onNavigate, navTestId }: Props) {
  return (
    <aside className={styles.aside} aria-label="Platform admin">
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden>
          BF
        </span>
        <div className={styles.brandText}>
          <span className={styles.brandName}>BotForge AI</span>
          <span className={styles.brandHint}>Platform admin</span>
        </div>
      </div>
      <nav className={styles.nav} aria-label="Platform sections" data-testid={navTestId}>
        {items.map((item) => {
          const active =
            pathname === item.href || (item.href !== "/superadmin" && pathname.startsWith(`${item.href}/`));
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
        <Link href="/dashboard" className={styles.footerLink} onClick={onNavigate}>
          ← Customer workspace
        </Link>
      </div>
    </aside>
  );
}
