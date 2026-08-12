import type { Metadata } from "next";

import { DashboardBots } from "@/components/dashboard/bots/dashboard-bots";

export const metadata: Metadata = {
  title: "Bots",
};

export default function DashboardBotsPage() {
  return <DashboardBots />;
}
