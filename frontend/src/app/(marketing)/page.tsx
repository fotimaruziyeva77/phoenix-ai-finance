import { FinanceLanding } from "@/components/home/finance-landing";

/**
 * The sales-bot landing sections (`hero`, `niche-section`, `how-it-works`, ...)
 * still live under `components/home/` but are no longer mounted: the product is
 * positioned as a finance advisor for entrepreneurs, not a bot builder.
 */
export default function HomePage() {
  return <FinanceLanding />;
}
