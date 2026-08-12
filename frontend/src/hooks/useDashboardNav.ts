"use client";

import { useLanguage } from "@/contexts/language-context";
import type { CustomerDashboardNavItem } from "@/config/customer-dashboard-nav";

/**
 * Raw nav routes — no labels here; labels come from translations.
 *
 * The product is a finance advisor for entrepreneurs, so the advisory tools lead.
 * Bot-building and lead-pipeline routes still exist under `/dashboard/bots` and
 * `/dashboard/leads` but are intentionally unlisted: they belong to the earlier
 * sales-bot positioning and would confuse an entrepreneur landing here.
 */
const NAV_ROUTES = [
  { href: "/dashboard", key: "overview" },
  { href: "/dashboard/business-plan", key: "businessPlan" },
  { href: "/dashboard/analytics", key: "analytics" },
  { href: "/dashboard/billing", key: "billing" },
  { href: "/dashboard/settings", key: "settings" },
] as const;

/** Returns translated nav items for the customer dashboard sidebar. */
export function useDashboardNav(): readonly CustomerDashboardNavItem[] {
  const { t } = useLanguage();
  return NAV_ROUTES.map(({ href, key }) => {
    const label = String(t(`dashboard.nav.${key}`));
    return { href, label, pageTitle: label };
  });
}

/** Longest href match wins so `/dashboard/settings/...` resolves to Settings. */
export function matchDashboardNavByPathname(
  items: readonly CustomerDashboardNavItem[],
  pathname: string,
): CustomerDashboardNavItem {
  const sorted = [...items].sort((a, b) => b.href.length - a.href.length);
  const hit = sorted.find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  return hit ?? items[0]!;
}
