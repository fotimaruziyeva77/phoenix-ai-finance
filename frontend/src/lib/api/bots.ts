import { ApiError, apiFetchWithAuth } from "@/lib/api/client";
import { toFriendlyGoalLabel, toFriendlyNicheLabel } from "@/lib/bot-domain/labels";

/** API DTO (snake_case from FastAPI). */
export type BotListItemDto = {
  id: string;
  name: string;
  niche: string | null;
  niche_id: string;
  goal_type: string;
  status: string;
  primary_channel?: string | null;
  updated_at: string | null;
};

export type BotListResponseDto = {
  items: BotListItemDto[];
};

export type WorkspaceBot = {
  id: string;
  name: string;
  nicheId: string;
  nicheLabel: string;
  goalType: "support" | "sales" | "faq" | "consulting";
  goalLabel: string;
  status: "draft" | "active" | "paused" | "archived" | "channel_pending";
  updatedAt: string | null;
};

function normalizeStatus(raw: string): WorkspaceBot["status"] {
  if (
    raw === "active" ||
    raw === "paused" ||
    raw === "draft" ||
    raw === "archived" ||
    raw === "channel_pending"
  )
    return raw;
  return "draft";
}

function normalizeGoalType(raw: string): WorkspaceBot["goalType"] {
  if (raw === "support" || raw === "sales" || raw === "faq" || raw === "consulting") return raw;
  return "support";
}

/** Maps a single API row to the workspace bot shape used in the UI. */
export function mapBotDto(dto: BotListItemDto): WorkspaceBot {
  const normalizedGoalType = normalizeGoalType(dto.goal_type);
  return {
    id: dto.id,
    name: dto.name,
    nicheId: dto.niche_id,
    nicheLabel: toFriendlyNicheLabel(dto.niche_id),
    goalType: normalizedGoalType,
    goalLabel: toFriendlyGoalLabel(normalizedGoalType),
    status: normalizeStatus(dto.status),
    updatedAt: dto.updated_at,
  };
}

/**
 * GET /api/v1/bots — authenticated workspace bot list.
 */
export async function fetchWorkspaceBots(accessToken: string | null): Promise<WorkspaceBot[]> {
  const data = await apiFetchWithAuth<BotListResponseDto>("/api/v1/bots", accessToken);
  return data.items.map(mapBotDto);
}

export function isBotsListUnavailableError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/** DELETE /api/v1/bots/{botId} — permanently deletes the bot. */
export async function deleteBot(
  accessToken: string | null,
  botId: string,
): Promise<void> {
  await apiFetchWithAuth<void>(
    `/api/v1/bots/${botId}`,
    accessToken,
    { method: "DELETE" },
  );
}

/** POST /api/v1/bots/{botId}/clone — creates a draft copy. */
export async function cloneBot(
  accessToken: string | null,
  botId: string,
): Promise<WorkspaceBot> {
  const data = await apiFetchWithAuth<BotListItemDto>(
    `/api/v1/bots/${botId}/clone`,
    accessToken,
    { method: "POST" },
  );
  return mapBotDto(data);
}
