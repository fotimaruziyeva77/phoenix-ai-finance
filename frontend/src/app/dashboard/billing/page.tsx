import { Suspense } from "react";
import type { Metadata } from "next";

import { BillingPage } from "@/components/dashboard/billing/billing-page";

export const metadata: Metadata = {
  title: "Billing",
};

export default function DashboardBillingPage() {
  return (
    <Suspense>
      <BillingPage />
    </Suspense>
  );
}
