import { apiFetchWithAuth } from "@/lib/api/client";

export type BotDetailDto = {
  id: string;
  owner_id: string;
  name: string;
  niche_id: string;
  goal_type: string;
  status: "draft" | "active" | "paused" | "archived";
  welcome_message: string | null;
  tone: string | null;
  language: string | null;
  short_description: string | null;
  provider_name: string;
  model_name: string | null;
  temperature: number | null;
  max_output_tokens: number | null;
  created_at: string;
  updated_at: string;
};

export type BotDetailUpdatePayload = {
  name?: string;
  welcome_message?: string | null;
  tone?: string | null;
  language?: string | null;
  short_description?: string | null;
  status?: "draft" | "active" | "paused" | "archived";
  provider_name?: string;
  model_name?: string | null;
  temperature?: number | null;
  max_output_tokens?: number | null;
};

export async function fetchBotDetail(accessToken: string | null, botId: string): Promise<BotDetailDto> {
  return apiFetchWithAuth<BotDetailDto>(`/api/v1/bots/${botId}`, accessToken, {
    method: "GET",
  });
}

export async function patchBotDetail(
  accessToken: string | null,
  botId: string,
  payload: BotDetailUpdatePayload,
): Promise<BotDetailDto> {
  return apiFetchWithAuth<BotDetailDto>(`/api/v1/bots/${botId}`, accessToken, {
    method: "PATCH",
    body: payload,
  });
}

export async function archiveBotDetail(accessToken: string | null, botId: string): Promise<BotDetailDto> {
  return apiFetchWithAuth<BotDetailDto>(`/api/v1/bots/${botId}/archive`, accessToken, {
    method: "POST",
  });
}

export async function deleteBotDetail(accessToken: string | null, botId: string): Promise<void> {
  await apiFetchWithAuth<void>(`/api/v1/bots/${botId}`, accessToken, {
    method: "DELETE",
  });
}
