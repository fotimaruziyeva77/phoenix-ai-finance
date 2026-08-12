import { ApiError, apiFetchWithAuth } from "@/lib/api/client";
import { toFriendlyNicheLabel } from "@/lib/bot-domain/labels";

/** GET /api/v1/leads item (snake_case from FastAPI). */
export type LeadListItemDto = {
  id: string;
  bot_id: string;
  conversation_id: string | null;
  niche_id: string;
  status: string;
  lead_temperature: string | null;
  lead_score: number | null;
  name: string | null;
  phone: string | null;
  summary: string | null;
  source_channel: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadListResponseDto = {
  items: LeadListItemDto[];
  total: number;
  next_cursor: string | null;
  has_more: boolean;
};

export type LeadPipelineStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "proposal"
  | "won"
  | "lost";

export type LeadTemperature = "cold" | "warm" | "hot";

export type WorkspaceLead = {
  id: string;
  botId: string;
  nicheId: string;
  nicheLabel: string;
  status: LeadPipelineStatus;
  temperature: LeadTemperature | null;
  /** ``null`` when the API did not set a score (0–100 when set). */
  leadScore: number | null;
  summary: string | null;
  /** Primary line for list UI */
  displayTitle: string;
  /** Secondary line when name is set (truncated summary preview). */
  subtitle: string | null;
  phone: string | null;
  createdAt: string;
  updatedAt: string;
};

export type FetchLeadsQuery = {
  status?: string;
  niche?: string;
  temperature?: string;
  limit?: number;
  offset?: number;
  after?: string;
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

function displayTitleFromDto(dto: LeadListItemDto): string {
  const name = dto.name?.trim();
  if (name) return name;
  const sum = dto.summary?.trim();
  if (sum) {
    const line = sum.split(/\n/)[0]?.trim() ?? "";
    if (line.length > 96) return `${line.slice(0, 93)}…`;
    return line || "Untitled lead";
  }
  return "Untitled lead";
}

function subtitleFromDto(dto: LeadListItemDto, displayTitle: string): string | null {
  const name = dto.name?.trim();
  if (!name || !dto.summary?.trim()) return null;
  const sum = dto.summary.trim();
  const line = sum.split(/\n/)[0]?.trim() ?? "";
  if (!line || line === displayTitle) return null;
  if (line.length > 120) return `${line.slice(0, 117)}…`;
  return line;
}

/** Maps GET /api/v1/leads list items to workspace UI shape (also used in tests). */
export function mapLeadListItemDto(dto: LeadListItemDto): WorkspaceLead {
  const title = displayTitleFromDto(dto);
  return {
    id: dto.id,
    botId: dto.bot_id,
    nicheId: dto.niche_id,
    nicheLabel: toFriendlyNicheLabel(dto.niche_id),
    status: normalizeStatus(dto.status),
    temperature: normalizeTemperature(dto.lead_temperature),
    leadScore: normalizeLeadScore(dto.lead_score),
    summary: dto.summary,
    displayTitle: title,
    subtitle: subtitleFromDto(dto, title),
    phone: dto.phone?.trim() ? dto.phone.trim() : null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function buildQueryString(q: FetchLeadsQuery): string {
  const p = new URLSearchParams();
  const limit = q.limit ?? 100;
  p.set("limit", String(Math.min(200, Math.max(1, limit))));
  if (q.offset !== undefined && q.offset > 0) p.set("offset", String(q.offset));
  if (q.status) p.set("status", q.status);
  if (q.niche?.trim()) p.set("niche", q.niche.trim());
  if (q.temperature) p.set("temperature", q.temperature);
  if (q.after) p.set("after", q.after);
  const s = p.toString();
  return s ? `?${s}` : "";
}

/**
 * GET /api/v1/leads — authenticated owner-scoped list.
 */
export async function fetchWorkspaceLeads(
  accessToken: string | null,
  query: FetchLeadsQuery = {},
): Promise<{ leads: WorkspaceLead[]; total: number; nextCursor: string | null; hasMore: boolean }> {
  const path = `/api/v1/leads${buildQueryString(query)}`;
  const data = await apiFetchWithAuth<LeadListResponseDto>(path, accessToken);
  return {
    leads: data.items.map(mapLeadListItemDto),
    total: data.total,
    nextCursor: data.next_cursor ?? null,
    hasMore: data.has_more ?? false,
  };
}

export function isLeadsListUnavailableError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
