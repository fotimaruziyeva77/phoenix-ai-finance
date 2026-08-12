import { apiFetch } from "@/lib/api/client";

/** Mirrors ``NicheCatalogItem`` from the FastAPI schema. */
export type NicheCatalogItemDto = {
  id: string;
  display_name: string;
  description: string;
  wizard_hint: string;
  icon_key: string;
  supported_goals: string[];
  onboarding_hints: string[];
  default_welcome_messages: Record<string, string>;
  visible: boolean;
};

export type NicheCatalogResponseDto = {
  schema_version: number;
  niches: NicheCatalogItemDto[];
};

/**
 * Public catalog — no auth. Used by wizard, landing, and label resolution after hydration.
 */
export async function fetchNicheCatalog(): Promise<NicheCatalogResponseDto> {
  return apiFetch<NicheCatalogResponseDto>("/api/v1/catalog/niches");
}
