import type { Metadata } from "next";

import { AnalyticsPage } from "@/components/dashboard/analytics/analytics-page";

export const metadata: Metadata = {
  title: "Analytics",
};

export default function DashboardAnalyticsPage() {
  return <AnalyticsPage />;
}
