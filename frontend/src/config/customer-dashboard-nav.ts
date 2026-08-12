/**
 * Customer (tenant admin) primary navigation.
 *
 * Superadmin or internal consoles should use a separate route prefix (e.g. `/admin`)
 * and their own nav config — keep that tree isolated from this list.
 */
export type CustomerDashboardNavItem = {
  readonly href: string;
  readonly label: string;
  /** Shown in the top bar for the active section */
  readonly pageTitle: string;
};

export const CUSTOMER_DASHBOARD_NAV: readonly CustomerDashboardNavItem[] = [
  { href: "/dashboard", label: "Overview", pageTitle: "Overview" },
  { href: "/dashboard/bots", label: "Bots", pageTitle: "Bots" },
  { href: "/dashboard/leads", label: "Leads", pageTitle: "Leads" },
  { href: "/dashboard/analytics", label: "Analytics", pageTitle: "Analytics" },
  { href: "/dashboard/billing", label: "Billing", pageTitle: "Billing & Plans" },
  { href: "/dashboard/settings", label: "Settings", pageTitle: "Settings" },
] as const;

/** Longest href match wins so `/dashboard/settings/...` resolves to Settings. */
export function matchCustomerDashboardNav(pathname: string): CustomerDashboardNavItem {
  const sorted = [...CUSTOMER_DASHBOARD_NAV].sort((a, b) => b.href.length - a.href.length);
  const hit = sorted.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  return hit ?? CUSTOMER_DASHBOARD_NAV[0]!;
}
