/** Marketing site navigation — single source for header + footer link rows. */

export type MarketingNavLink = {
  readonly label: string;
  readonly href: string;
  /** Key into the finance copy `tools` map; falls back to `label` when absent. */
  readonly toolKey?: "chat" | "plan" | "credit" | "tax";
};

export const MARKETING_NAV_LINKS: readonly MarketingNavLink[] = [
  { label: "Maslahatchi", href: "/maslahatchi", toolKey: "chat" },
  { label: "Biznes-reja", href: "/biznes-reja", toolKey: "plan" },
  { label: "Kredit", href: "/kredit", toolKey: "credit" },
  { label: "Soliq", href: "/soliq", toolKey: "tax" },
] as const;
