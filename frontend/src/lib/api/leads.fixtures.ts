import type { LeadListItemDto } from "./leads";

/** Minimal valid API list row for tests — matches FastAPI ``LeadListItem`` JSON shape. */
export function sampleLeadListItemDto(overrides: Partial<LeadListItemDto> = {}): LeadListItemDto {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    bot_id: "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    conversation_id: null,
    niche_id: "education",
    status: "new",
    lead_temperature: null,
    lead_score: null,
    name: null,
    phone: null,
    summary: "Wants a demo next week",
    source_channel: "telegram",
    created_at: "2026-01-15T10:00:00.000Z",
    updated_at: "2026-01-15T11:00:00.000Z",
    ...overrides,
  };
}
