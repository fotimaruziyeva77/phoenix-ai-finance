import type { NicheCatalogItemDto } from "@/lib/api/niche-catalog";

import { FALLBACK_SUPPORTED_NICHE_IDS } from "./niche-fallback";

/** Mirrors default catalog display names when API is unavailable (keep aligned with backend). */
const FALLBACK_DISPLAY_NAMES: Record<string, string> = {
  education: "Education",
  healthcare: "Healthcare / Clinic",
  dev_agency: "Dev / Agency",
  services: "Services",
};

let cachedItems: NicheCatalogItemDto[] | null = null;
let cachedSchemaVersion: number | null = null;

export function setNicheCatalogCache(data: { niches: NicheCatalogItemDto[]; schema_version: number } | null): void {
  if (!data) {
    cachedItems = null;
    cachedSchemaVersion = null;
    return;
  }
  cachedItems = data.niches;
  cachedSchemaVersion = data.schema_version;
}

export function getNicheCatalogSchemaVersion(): number | null {
  return cachedSchemaVersion;
}

export function getNicheCatalogItemsFromCache(): NicheCatalogItemDto[] {
  return cachedItems ?? [];
}

export function getNicheIdSet(): Set<string> {
  if (cachedItems && cachedItems.length > 0) {
    return new Set(cachedItems.map((n) => n.id));
  }
  return new Set<string>(FALLBACK_SUPPORTED_NICHE_IDS);
}

export function getNicheDisplayName(id: string): string {
  const row = cachedItems?.find((n) => n.id === id);
  if (row) return row.display_name;
  return FALLBACK_DISPLAY_NAMES[id] ?? id;
}
