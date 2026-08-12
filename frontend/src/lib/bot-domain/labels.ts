import type { SupportedGoalType } from "./constants";
import { getNicheDisplayName } from "./niche-catalog-cache";

const GOAL_LABELS: Record<SupportedGoalType, string> = {
  support: "Support",
  sales: "Sales",
  faq: "FAQ",
  consulting: "Consulting",
};

export function toFriendlyNicheLabel(nicheId: string | null | undefined): string {
  if (!nicheId) return "—";
  return getNicheDisplayName(nicheId);
}

export function toFriendlyGoalLabel(goalType: string | null | undefined): string {
  if (!goalType) return "—";
  return GOAL_LABELS[goalType as SupportedGoalType] ?? goalType;
}
