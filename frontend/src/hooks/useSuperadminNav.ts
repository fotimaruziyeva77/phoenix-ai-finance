"use client";

import { useLanguage } from "@/contexts/language-context";
import type { SuperadminNavItem } from "@/config/superadmin-nav";

const SUPERADMIN_ROUTES = [
  { href: "/superadmin",               key: "overview"      },
  { href: "/superadmin/users",         key: "users"         },
  { href: "/superadmin/bots",          key: "bots"          },
  { href: "/superadmin/billing",       key: "billing"       },
  { href: "/superadmin/ai-usage",      key: "aiUsage"       },
  { href: "/superadmin/audit-log",     key: "auditLog"      },
  { href: "/superadmin/feature-flags", key: "featureFlags"  },
  { href: "/superadmin/support",        key: "support"       },
  { href: "/superadmin/coupons",        key: "coupons"       },
  { href: "/superadmin/analytics",      key: "analytics"     },
  { href: "/superadmin/abuse",          key: "abuse"         },
  { href: "/superadmin/export",         key: "export"        },
  { href: "/superadmin/campaigns",      key: "campaigns"     },
  { href: "/superadmin/webhook-logs",   key: "webhookLogs"   },
] as const;

/** Returns translated nav items for the superadmin shell. */
export function useSuperadminNav(): readonly SuperadminNavItem[] {
  const { t } = useLanguage();
  return SUPERADMIN_ROUTES.map(({ href, key }) => {
    const label = String(t(`superadmin.nav.${key}`));
    return { href, label, pageTitle: label };
  });
}

/** Longest href match wins. */
export function matchSuperadminNavByPathname(
  items: readonly SuperadminNavItem[],
  pathname: string,
): SuperadminNavItem {
  const sorted = [...items].sort((a, b) => b.href.length - a.href.length);
  const hit = sorted.find(
    (item) =>
      pathname === item.href ||
      (item.href !== "/superadmin" && pathname.startsWith(`${item.href}/`)),
  );
  return hit ?? items[0]!;
}
