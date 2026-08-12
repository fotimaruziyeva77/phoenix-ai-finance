import { apiFetchWithAuth } from "@/lib/api/client";
import type { LeadPipelineStatus, LeadTemperature } from "@/lib/api/leads";
import { toFriendlyNicheLabel } from "@/lib/bot-domain/labels";

/** GET/PATCH ``/api/v1/leads/{id}`` — snake_case from FastAPI ``LeadRead``. */
export type LeadDetailDto = {
  id: string;
  bot_id: string;
  owner_id: string;
  conversation_id: string | null;
  niche_id: string;
  lead_score: number | null;
  lead_temperature: string | null;
  status: string;
  name: string | null;
  phone: string | null;
  summary: string | null;
  notes: string | null;
  source_channel: string | null;
  collected_data_json: Record<string, unknown> | null;
  assignee_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadDetail = {
  id: string;
  botId: string;
  nicheId: string;
  nicheLabel: string;
  conversationId: string | null;
  leadScore: number | null;
  temperature: LeadTemperature | null;
  status: LeadPipelineStatus;
  name: string | null;
  phone: string | null;
  summary: string | null;
  notes: string | null;
  sourceChannel: string | null;
  collectedData: Record<string, unknown> | null;
  assigneeUserId: string | null;
  createdAt: string;
  updatedAt: string;
};

/** Full pipeline row save from the detail form (all fields sent so the server applies a consistent snapshot). */
export type LeadPipelineFormPayload = {
  status: LeadPipelineStatus;
  lead_temperature: LeadTemperature | null;
  notes: string | null;
  assignee_user_id?: string | null;
};

function normalizeStatus(raw: string): LeadPipelineStatus {
  if (
    raw === "new" ||
    raw === "contacted" ||
    raw === "qualified" ||
    raw === "proposal" ||
    raw === "won" ||
    raw === "lost"
  ) {
    return raw;
  }
  return "new";
}

function normalizeTemperature(raw: string | null | undefined): LeadTemperature | null {
  if (raw === "cold" || raw === "warm" || raw === "hot") return raw;
  return null;
}

function normalizeLeadScore(raw: number | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  if (!Number.isFinite(raw)) return null;
  const n = Math.round(raw);
  if (n < 0 || n > 100) return null;
  return n;
}

export function mapLeadDetailDto(dto: LeadDetailDto): LeadDetail {
  return {
    id: dto.id,
    botId: dto.bot_id,
    nicheId: dto.niche_id,
    nicheLabel: toFriendlyNicheLabel(dto.niche_id),
    conversationId: dto.conversation_id,
    leadScore: normalizeLeadScore(dto.lead_score),
    temperature: normalizeTemperature(dto.lead_temperature),
    status: normalizeStatus(dto.status),
    name: dto.name?.trim() ? dto.name.trim() : null,
    phone: dto.phone?.trim() ? dto.phone.trim() : null,
    summary: dto.summary ?? null,
    notes: dto.notes ?? null,
    sourceChannel: dto.source_channel?.trim() ? dto.source_channel.trim() : null,
    collectedData:
      dto.collected_data_json !== null && typeof dto.collected_data_json === "object" && !Array.isArray(dto.collected_data_json)
        ? (dto.collected_data_json as Record<string, unknown>)
        : null,
    assigneeUserId: dto.assignee_user_id ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export async function fetchLeadDetail(accessToken: string | null, leadId: string): Promise<LeadDetail> {
  const dto = await apiFetchWithAuth<LeadDetailDto>(`/api/v1/leads/${leadId}`, accessToken, {
    method: "GET",
  });
  return mapLeadDetailDto(dto);
}

/** PATCH ``/api/v1/leads/{id}/status`` — returns updated ``LeadRead``. */
export async function patchLeadPipeline(
  accessToken: string | null,
  leadId: string,
  payload: LeadPipelineFormPayload,
): Promise<LeadDetail> {
  const dto = await apiFetchWithAuth<LeadDetailDto>(`/api/v1/leads/${leadId}/status`, accessToken, {
    method: "PATCH",
    body: {
      status: payload.status,
      lead_temperature: payload.lead_temperature,
      notes: payload.notes,
      ...(payload.assignee_user_id !== undefined ? { assignee_user_id: payload.assignee_user_id } : {}),
    },
  });
  return mapLeadDetailDto(dto);
}
