/**
 * Offline / SSR fallback ids — must match backend ``list_supported_niches`` order and ids.
 * Display strings live in ``niche-catalog-cache`` for sync helpers when the API has not loaded.
 */

export const FALLBACK_SUPPORTED_NICHE_IDS = ["education", "healthcare", "dev_agency", "services"] as const;

export type FallbackNicheId = (typeof FALLBACK_SUPPORTED_NICHE_IDS)[number];
