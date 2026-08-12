"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  connectBotTelegram,
  disconnectBotTelegram,
  fetchBotTelegramStatus,
  type BotTelegramStatusDto,
} from "@/lib/api/bot-telegram";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";

type LoadStatus = "idle" | "loading" | "success" | "error";

export type UseBotTelegramResult = {
  loadStatus: LoadStatus;
  status: BotTelegramStatusDto | null;
  loadError: string | null;
  actionError: string | null;
  successMessage: string | null;
  isConnecting: boolean;
  isDisconnecting: boolean;
  refresh: () => Promise<void>;
  connect: (botToken: string) => Promise<void>;
  disconnect: () => Promise<void>;
};

export function useBotTelegram(botId: string, enabled: boolean): UseBotTelegramResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [loadStatus, setLoadStatus] = useState<LoadStatus>("idle");
  const [status, setStatus] = useState<BotTelegramStatusDto | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setLoadStatus("error");
      setLoadError("Your session expired. Sign in again.");
      setStatus(null);
      return;
    }
    setLoadStatus("loading");
    setLoadError(null);
    try {
      const next = await fetchBotTelegramStatus(accessToken, botId);
      setStatus(next);
      setLoadStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setLoadError("Bot not found.");
      } else if (error instanceof ApiError && error.status === 403) {
        setLoadError("You do not have access to this bot.");
      } else if (error instanceof ApiError && error.status === 401) {
        setLoadError("Your session expired. Sign in again.");
      } else {
        setLoadError("Could not load Telegram status right now.");
      }
      setStatus(null);
      setLoadStatus("error");
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !enabled) return;
    void load();
  }, [enabled, hydrated, load]);

  const connect = useCallback(
    async (botToken: string) => {
      if (!canUseAuthenticatedApi) {
        setActionError("Your session expired. Sign in again.");
        setSuccessMessage(null);
        return;
      }
      const trimmed = botToken.trim();
      if (trimmed.length < 10) {
        setActionError("Paste the full token from BotFather (usually 45+ characters).");
        setSuccessMessage(null);
        return;
      }
      setIsConnecting(true);
      setActionError(null);
      setSuccessMessage(null);
      try {
        const next = await connectBotTelegram(accessToken, botId, trimmed);
        setStatus(next);
        if (next.channel_status === "active") {
          setSuccessMessage("Telegram connected. Your token is stored securely and is not shown again.");
        } else {
          setSuccessMessage("Request completed. Check connection status below.");
        }
      } catch (error) {
        setActionError(parseApiErrorMessage(error));
      } finally {
        setIsConnecting(false);
      }
    },
    [accessToken, botId, canUseAuthenticatedApi],
  );

  const disconnect = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setActionError("Your session expired. Sign in again.");
      setSuccessMessage(null);
      return;
    }
    setIsDisconnecting(true);
    setActionError(null);
    setSuccessMessage(null);
    try {
      await disconnectBotTelegram(accessToken, botId);
      await load();
      setSuccessMessage("Telegram disconnected. The bot token was removed from this workspace.");
    } catch (error) {
      setActionError(parseApiErrorMessage(error));
    } finally {
      setIsDisconnecting(false);
    }
  }, [accessToken, botId, load, canUseAuthenticatedApi]);

  return {
    loadStatus,
    status,
    loadError,
    actionError,
    successMessage,
    isConnecting,
    isDisconnecting,
    refresh: load,
    connect,
    disconnect,
  };
}
