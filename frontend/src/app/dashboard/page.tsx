import type { Metadata } from "next";

import { FinanceHome } from "@/components/dashboard/overview/finance-home";

export const metadata: Metadata = {
  title: "Overview",
};

/**
 * `DashboardOverview` (the bot-building walkthrough) still exists under
 * `components/dashboard/overview/` but reflects the old positioning; the
 * signed-in home now opens the finance advisory tools.
 */
export default function DashboardOverviewPage() {
  return <FinanceHome />;
}
