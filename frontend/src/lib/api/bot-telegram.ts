import { apiFetchWithAuth } from "@/lib/api/client";

/** Matches FastAPI ``BotTelegramStatusResponse`` (no token fields). */
export type TelegramChannelStatus = "draft" | "channel_pending" | "active" | "failed_validation";

export type BotTelegramStatusDto = {
  channel_status: TelegramChannelStatus;
  configured: boolean;
  connected: boolean;
  bot_username: string | null;
  last_verified_at: string | null;
  webhook_url_configured: boolean;
  last_error_code: string | null;
};

/** Matches ``BotTelegramTokenValidateResponse`` (dry-run token check). */
export type BotTelegramTokenValidateDto = {
  valid: true;
  bot_username: string | null;
  telegram_bot_id: number;
};

export async function fetchBotTelegramStatus(
  accessToken: string | null,
  botId: string,
): Promise<BotTelegramStatusDto> {
  return apiFetchWithAuth<BotTelegramStatusDto>(`/api/v1/bots/${botId}/telegram/status`, accessToken, {
    method: "GET",
  });
}

export async function connectBotTelegram(
  accessToken: string | null,
  botId: string,
  botToken: string,
): Promise<BotTelegramStatusDto> {
  return apiFetchWithAuth<BotTelegramStatusDto>(`/api/v1/bots/${botId}/telegram/connect`, accessToken, {
    method: "POST",
    body: { bot_token: botToken.trim() },
  });
}

export async function validateBotTelegramToken(
  accessToken: string | null,
  botId: string,
  botToken: string,
): Promise<BotTelegramTokenValidateDto> {
  return apiFetchWithAuth<BotTelegramTokenValidateDto>(
    `/api/v1/bots/${botId}/telegram/token/validate`,
    accessToken,
    { method: "POST", body: { bot_token: botToken.trim() } },
  );
}

export async function disconnectBotTelegram(accessToken: string | null, botId: string): Promise<void> {
  await apiFetchWithAuth<undefined>(`/api/v1/bots/${botId}/telegram/disconnect`, accessToken, {
    method: "POST",
  });
}

export async function startBotTelegramProvisioning(
  accessToken: string | null,
  botId: string,
): Promise<BotTelegramStatusDto> {
  return apiFetchWithAuth<BotTelegramStatusDto>(
    `/api/v1/bots/${botId}/telegram/provisioning/start`,
    accessToken,
    { method: "POST" },
  );
}

export async function syncBotTelegramWebhook(
  accessToken: string | null,
  botId: string,
): Promise<BotTelegramStatusDto> {
  return apiFetchWithAuth<BotTelegramStatusDto>(
    `/api/v1/bots/${botId}/telegram/webhook/sync`,
    accessToken,
    { method: "POST" },
  );
}
