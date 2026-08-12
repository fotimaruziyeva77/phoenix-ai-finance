import { getNicheIdSet } from "./niche-catalog-cache";
import { FALLBACK_SUPPORTED_NICHE_IDS } from "./niche-fallback";

/** @deprecated Use catalog-backed ``isSupportedNicheId`` — kept for searchability in migrations. */
export const SUPPORTED_NICHE_IDS = FALLBACK_SUPPORTED_NICHE_IDS;

/** Runtime niche id from API (not a closed union — avoids compile-time drift). */
export type NicheId = string;

export const SUPPORTED_GOAL_TYPES = ["support", "sales", "faq", "consulting"] as const;

export type SupportedGoalType = (typeof SUPPORTED_GOAL_TYPES)[number];

const goalSet = new Set<string>(SUPPORTED_GOAL_TYPES);

/** True when id is in the latest catalog (or fallback ids before hydration). */
export function isSupportedNicheId(value: string | null | undefined): value is NicheId {
  return typeof value === "string" && getNicheIdSet().has(value);
}

export function isSupportedGoalType(value: string | null | undefined): value is SupportedGoalType {
  return typeof value === "string" && goalSet.has(value);
}
