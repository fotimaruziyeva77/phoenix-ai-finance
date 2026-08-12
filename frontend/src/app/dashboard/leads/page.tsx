import type { Metadata } from "next";

import { DashboardLeads } from "@/components/dashboard/leads/dashboard-leads";

export const metadata: Metadata = {
  title: "Leads",
};

export default function DashboardLeadsPage() {
  return <DashboardLeads />;
}
