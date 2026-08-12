"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { DashboardTopbar } from "@/components/dashboard/dashboard-topbar";
import { useAuth } from "@/hooks/useAuth";
import { useSuperadminNav, matchSuperadminNavByPathname } from "@/hooks/useSuperadminNav";

import { SuperadminSidebar } from "./superadmin-sidebar";
import shellStyles from "@/components/dashboard/dashboard-shell.module.css";

type Props = {
  children: ReactNode;
};

function initialsFromEmail(email: string): string {
  const head = email.trim().slice(0, 1).toUpperCase();
  return head || "?";
}

export function SuperadminShell({ children }: Props) {
  const pathname = usePathname() ?? "/superadmin";
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const navItems = useSuperadminNav();

  const active = matchSuperadminNavByPathname(navItems, pathname);
  const email = user?.email ?? "—";
  const initial = user?.full_name?.trim().slice(0, 1).toUpperCase() ?? initialsFromEmail(email);

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
    <div className={shellStyles.root}>
      <div className={shellStyles.body}>
        <div className={shellStyles.sidebarDesktop}>
          <SuperadminSidebar items={navItems} pathname={pathname} navTestId="superadmin-nav-desktop" />
        </div>

        <div
          className={`${shellStyles.sidebarMobile} ${menuOpen ? shellStyles.sidebarMobileOpen : ""}`}
          aria-hidden={!menuOpen}
        >
          <button
            type="button"
            className={shellStyles.backdrop}
            aria-label="Dismiss menu overlay"
            onClick={closeMenu}
          />
          <div className={shellStyles.drawer} id="superadmin-nav-drawer">
            <SuperadminSidebar
              items={navItems}
              pathname={pathname}
              onNavigate={closeMenu}
              navTestId="superadmin-nav-mobile"
            />
          </div>
        </div>

        <div className={shellStyles.column}>
          <DashboardTopbar
            pageTitle={active.pageTitle}
            productSubtitle="Platform operations"
            userEmail={email}
            userInitial={initial}
            onLogout={() => logout()}
            menuOpen={menuOpen}
            onMenuToggle={toggleMenu}
            navDrawerId="superadmin-nav-drawer"
          />
          <main className={shellStyles.main}>
            <div className={shellStyles.pageInner}>{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
