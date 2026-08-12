import type { Metadata } from "next";

import { BusinessPlanView } from "@/components/dashboard/finance/business-plan-view";

export const metadata: Metadata = {
  title: "Biznes-reja",
};

export default function BusinessPlanPage() {
  return <BusinessPlanView />;
}
