import type { Metadata } from "next";

import { FinanceToolPage } from "@/components/dashboard/finance/finance-tool-page";

export const metadata: Metadata = {
  title: "Soliq hisob-kitobi",
  description: "2026-yil soliq rejimlarini solishtiring va eng arzonini tanlang.",
};

/**
 * Public advisory route — no auth, no backend. The engine is pure client-side
 * arithmetic, so a first-time visitor gets a real answer before signing up.
 */
export default function Page() {
  return <FinanceToolPage tool="tax" />;
}
