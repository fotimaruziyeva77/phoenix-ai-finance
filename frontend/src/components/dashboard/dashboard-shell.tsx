"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { useAuth } from "@/hooks/useAuth";
import { matchDashboardNavByPathname, useDashboardNav } from "@/hooks/useDashboardNav";

import { DashboardSidebar } from "./dashboard-sidebar";
import sidebarStyles from "./dashboard-sidebar.module.css";
import { DashboardTopbar } from "./dashboard-topbar";
import styles from "./dashboard-shell.module.css";

type Props = {
  children: ReactNode;
};

function initialsFromEmail(email: string): string {
  const head = email.trim().slice(0, 1).toUpperCase();
  return head || "?";
}

export function DashboardShell({ children }: Props) {
  const pathname = usePathname() ?? "/dashboard";
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const navItems = useDashboardNav();

  const active = matchDashboardNavByPathname(navItems, pathname);
  const email = user?.email ?? "—";
  const initial = user?.full_name?.trim().slice(0, 1).toUpperCase() ?? initialsFromEmail(email);

  const platformAdminFooter =
    user?.role === "superadmin" ? (
      <Link
        href="/superadmin"
        className={sidebarStyles.footerLink}
        data-testid="nav-platform-admin"
      >
        Platform admin
      </Link>
    ) : null;

  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const toggleMenu = useCallback(() => setMenuOpen((o) => !o), []);

  useEffect(() => {
    closeMenu();
  }, [pathname, closeMenu]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMenu();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen, closeMenu]);

  return (
    <div className={styles.root}>
      <div className={styles.body}>
        <div className={styles.sidebarDesktop}>
          <DashboardSidebar
            items={navItems}
            pathname={pathname}
            navTestId="dashboard-nav-desktop"
            footerAddon={platformAdminFooter}
          />
        </div>

        <div
          className={`${styles.sidebarMobile} ${menuOpen ? styles.sidebarMobileOpen : ""}`}
          aria-hidden={!menuOpen}
        >
          <button
            type="button"
            className={styles.backdrop}
            aria-label="Dismiss menu overlay"
            onClick={closeMenu}
          />
          <div className={styles.drawer} id="dashboard-nav-drawer">
            <DashboardSidebar
              items={navItems}
              pathname={pathname}
              onNavigate={closeMenu}
              navTestId="dashboard-nav-mobile"
              footerAddon={platformAdminFooter}
            />
          </div>
        </div>

        <div className={styles.column}>
          <DashboardTopbar
            pageTitle={active.pageTitle}
            userEmail={email}
            userInitial={initial}
            onLogout={() => logout()}
            menuOpen={menuOpen}
            onMenuToggle={toggleMenu}
          />
          <main className={styles.main}>
            <div className={styles.pageInner}>{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
