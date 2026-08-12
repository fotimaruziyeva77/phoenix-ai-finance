/**
 * Platform operator navigation (isolated from ``customer-dashboard-nav``).
 */
export type SuperadminNavItem = {
  readonly href: string;
  readonly label: string;
  readonly pageTitle: string;
};

export const SUPERADMIN_NAV: readonly SuperadminNavItem[] = [
  { href: "/superadmin", label: "Overview", pageTitle: "Platform overview" },
  { href: "/superadmin/users", label: "Users", pageTitle: "Users" },
  { href: "/superadmin/bots", label: "Bots", pageTitle: "Bots" },
] as const;

export function matchSuperadminNav(pathname: string): SuperadminNavItem {
  const sorted = [...SUPERADMIN_NAV].sort((a, b) => b.href.length - a.href.length);
  const hit = sorted.find(
    (item) => pathname === item.href || (item.href !== "/superadmin" && pathname.startsWith(`${item.href}/`)),
  );
  return hit ?? SUPERADMIN_NAV[0]!;
}
