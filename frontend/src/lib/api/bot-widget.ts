import { apiFetchWithAuth } from "@/lib/api/client";

export type BotWidgetConfigDto = {
  id: string;
  bot_id: string;
  public_widget_key: string;
  is_enabled: boolean;
  allowed_domains: string[];
  theme: string | null;
  welcome_text: string | null;
  widget_settings: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type BotWidgetPatchPayload = {
  is_enabled?: boolean;
  allowed_domains_json?: string[];
  theme?: string | null;
  welcome_text?: string | null;
};

export async function fetchBotWidgetConfig(
  accessToken: string | null,
  botId: string,
): Promise<BotWidgetConfigDto> {
  return apiFetchWithAuth<BotWidgetConfigDto>(`/api/v1/bots/${botId}/widget`, accessToken, {
    method: "GET",
  });
}

export async function patchBotWidgetConfig(
  accessToken: string | null,
  botId: string,
  payload: BotWidgetPatchPayload,
): Promise<BotWidgetConfigDto> {
  return apiFetchWithAuth<BotWidgetConfigDto>(`/api/v1/bots/${botId}/widget`, accessToken, {
    method: "PATCH",
    body: payload,
  });
}
