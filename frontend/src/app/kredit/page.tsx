import type { Metadata } from "next";

import { FinanceToolPage } from "@/components/dashboard/finance/finance-tool-page";

export const metadata: Metadata = {
  title: "Kredit va imtiyozlar",
  description: "Kredit yukini hisoblang, banklarni solishtiring va sizga tegishli davlat imtiyozli dasturlarini toping.",
};

/**
 * Public advisory route — no auth, no backend. The engine is pure client-side
 * arithmetic, so a first-time visitor gets a real answer before signing up.
 */
export default function Page() {
  return <FinanceToolPage tool="credit" />;
}
