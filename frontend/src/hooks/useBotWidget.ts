"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  fetchBotWidgetConfig,
  patchBotWidgetConfig,
  type BotWidgetConfigDto,
  type BotWidgetPatchPayload,
} from "@/lib/api/bot-widget";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";

type WidgetLoadStatus = "idle" | "loading" | "success" | "error";

export type UseBotWidgetResult = {
  loadStatus: WidgetLoadStatus;
  config: BotWidgetConfigDto | null;
  loadError: string | null;
  saveError: string | null;
  saveSuccess: string | null;
  isSaving: boolean;
  refresh: () => void;
  save: (payload: BotWidgetPatchPayload) => Promise<void>;
};

export function useBotWidget(botId: string, enabled: boolean): UseBotWidgetResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [loadStatus, setLoadStatus] = useState<WidgetLoadStatus>("idle");
  const [config, setConfig] = useState<BotWidgetConfigDto | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setLoadStatus("error");
      setLoadError("Your session expired. Sign in again.");
      setConfig(null);
      return;
    }
    setLoadStatus("loading");
    setLoadError(null);
    try {
      const next = await fetchBotWidgetConfig(accessToken, botId);
      setConfig(next);
      setLoadStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setLoadError("Bot not found.");
      } else if (error instanceof ApiError && error.status === 403) {
        setLoadError("You do not have access to this bot.");
      } else if (error instanceof ApiError && error.status === 401) {
        setLoadError("Your session expired. Sign in again.");
      } else {
        setLoadError("Could not load widget settings right now.");
      }
      setConfig(null);
      setLoadStatus("error");
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !enabled) return;
    void load();
  }, [enabled, hydrated, load]);

  const save = useCallback(
    async (payload: BotWidgetPatchPayload) => {
      if (!canUseAuthenticatedApi) {
        setSaveError("Your session expired. Sign in again.");
        setSaveSuccess(null);
        return;
      }
      setIsSaving(true);
      setSaveError(null);
      setSaveSuccess(null);
      try {
        const updated = await patchBotWidgetConfig(accessToken, botId, payload);
        setConfig(updated);
        setSaveSuccess("Widget settings saved.");
      } catch (error) {
        setSaveError(parseApiErrorMessage(error));
      } finally {
        setIsSaving(false);
      }
    },
    [accessToken, botId, canUseAuthenticatedApi],
  );

  return {
    loadStatus,
    config,
    loadError,
    saveError,
    saveSuccess,
    isSaving,
    refresh: load,
    save,
  };
}
