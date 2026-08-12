import type { Metadata } from "next";

import { FinanceToolPage } from "@/components/dashboard/finance/finance-tool-page";

export const metadata: Metadata = {
  title: "Biznes-reja",
  description: "Biznesingiz foyda beradimi? Zararsizlik nuqtasi, qoplanish muddati, soliq rejimi va lokatsiya taqqoslash — 30 soniyada.",
};

/**
 * Public advisory route — no auth, no backend. The engine is pure client-side
 * arithmetic, so a first-time visitor gets a real answer before signing up.
 */
export default function Page() {
  return <FinanceToolPage tool="plan" />;
}
