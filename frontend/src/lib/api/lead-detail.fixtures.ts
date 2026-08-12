import type { LeadDetailDto } from "./lead-detail";

export function sampleLeadDetailDto(overrides: Partial<LeadDetailDto> = {}): LeadDetailDto {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    bot_id: "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    owner_id: "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    conversation_id: null,
    niche_id: "education",
    lead_score: 55,
    lead_temperature: "warm",
    status: "qualified",
    name: "Jamie",
    phone: "+15559876543",
    summary: "Looking for onboarding help.\nBudget Q2.",
    notes: "Left voicemail",
    source_channel: "telegram",
    collected_data_json: { company: "Acme", seats: 12 },
    assignee_user_id: null,
    created_at: "2026-02-01T09:00:00.000Z",
    updated_at: "2026-02-02T14:30:00.000Z",
    ...overrides,
  };
}
