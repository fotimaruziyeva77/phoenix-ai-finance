"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  fetchTelegramLinkStatus,
  unlinkTelegram,
  type TelegramLinkStatus,
} from "@/lib/api/telegram-linking";

export type UseTelegramLinkingResult = {
  status: TelegramLinkStatus | null;
  loading: boolean;
  unlinking: boolean;
  errorMessage: string | null;
  refetch: () => void;
  unlink: () => Promise<void>;
};

export function useTelegramLinking(): UseTelegramLinkingResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<TelegramLinkStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [unlinking, setUnlinking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setStatus(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      const s = await fetchTelegramLinkStatus(accessToken);
      setStatus(s);
    } catch {
      setErrorMessage("Could not load Telegram status.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  const handleUnlink = useCallback(async () => {
    setUnlinking(true);
    setErrorMessage(null);
    try {
      await unlinkTelegram(accessToken);
      // Refetch to get updated status
      await load();
    } catch {
      setErrorMessage("Could not unlink Telegram.");
    } finally {
      setUnlinking(false);
    }
  }, [accessToken, load]);

  return {
    status,
    loading,
    unlinking,
    errorMessage,
    refetch: load,
    unlink: handleUnlink,
  };
}
