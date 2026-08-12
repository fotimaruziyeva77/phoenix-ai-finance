import { apiFetchWithAuth } from "@/lib/api/client";

// ─── Types ───────────────────────────────────────────────────────────────────

export type TelegramLinkStatusDto = {
  is_linked: boolean;
  telegram_chat_id: string | null;
  linked_at: string | null;
  link_url: string | null;
  bot_username: string | null;
};

export type TelegramUnlinkResponseDto = {
  success: boolean;
};

// ─── Mapped types ────────────────────────────────────────────────────────────

export type TelegramLinkStatus = {
  isLinked: boolean;
  telegramChatId: string | null;
  linkedAt: string | null;
  linkUrl: string | null;
  botUsername: string | null;
};

function mapStatus(dto: TelegramLinkStatusDto): TelegramLinkStatus {
  return {
    isLinked: dto.is_linked,
    telegramChatId: dto.telegram_chat_id,
    linkedAt: dto.linked_at,
    linkUrl: dto.link_url,
    botUsername: dto.bot_username,
  };
}

// ─── API functions ───────────────────────────────────────────────────────────

export async function fetchTelegramLinkStatus(
  accessToken: string | null,
): Promise<TelegramLinkStatus> {
  const data = await apiFetchWithAuth<TelegramLinkStatusDto>(
    "/api/v1/settings/telegram",
    accessToken,
  );
  return mapStatus(data);
}

export async function unlinkTelegram(
  accessToken: string | null,
): Promise<boolean> {
  const data = await apiFetchWithAuth<TelegramUnlinkResponseDto>(
    "/api/v1/settings/telegram",
    accessToken,
    { method: "DELETE" },
  );
  return data.success;
}
