"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  archiveBotDetail,
  deleteBotDetail,
  type BotDetailDto,
  patchBotDetail,
  fetchBotDetail,
  type BotDetailUpdatePayload,
} from "@/lib/api/bot-detail";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";

type BotDetailStatus = "idle" | "loading" | "success" | "error";

type UseBotDetailResult = {
  status: BotDetailStatus;
  bot: BotDetailDto | null;
  errorMessage: string | null;
  saveError: string | null;
  saveSuccess: string | null;
  isSaving: boolean;
  isArchiving: boolean;
  isDeleting: boolean;
  refresh: () => void;
  save: (payload: BotDetailUpdatePayload) => Promise<void>;
  archive: () => Promise<void>;
  hardDelete: () => Promise<boolean>;
};

export function useBotDetail(botId: string): UseBotDetailResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<BotDetailStatus>("idle");
  const [bot, setBot] = useState<BotDetailDto | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setStatus("error");
      setErrorMessage("Your session expired. Sign in again.");
      setBot(null);
      return;
    }
    setStatus("loading");
    setErrorMessage(null);
    try {
      const next = await fetchBotDetail(accessToken, botId);
      setBot(next);
      setStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setErrorMessage("Bot not found.");
      } else if (error instanceof ApiError && error.status === 403) {
        setErrorMessage("You do not have access to this bot.");
      } else if (error instanceof ApiError && error.status === 401) {
        setErrorMessage("Your session expired. Sign in again.");
      } else {
        setErrorMessage("Could not load bot details right now.");
      }
      setBot(null);
      setStatus("error");
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  const save = useCallback(
    async (payload: BotDetailUpdatePayload) => {
      if (!canUseAuthenticatedApi) {
        setSaveError("Your session expired. Sign in again.");
        setSaveSuccess(null);
        return;
      }
      setIsSaving(true);
      setSaveError(null);
      setSaveSuccess(null);
      try {
        const updated = await patchBotDetail(accessToken, botId, payload);
        setBot(updated);
        setSaveSuccess("Changes saved.");
      } catch (error) {
        setSaveError(parseApiErrorMessage(error));
      } finally {
        setIsSaving(false);
      }
    },
    [accessToken, botId, canUseAuthenticatedApi],
  );

  const archive = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setSaveError("Your session expired. Sign in again.");
      setSaveSuccess(null);
      return;
    }
    setIsArchiving(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      const updated = await archiveBotDetail(accessToken, botId);
      setBot(updated);
      setSaveSuccess("Bot archived. It stays visible with archived status.");
    } catch (error) {
      setSaveError(parseApiErrorMessage(error));
    } finally {
      setIsArchiving(false);
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  const hardDelete = useCallback(async (): Promise<boolean> => {
    if (!canUseAuthenticatedApi) {
      setSaveError("Your session expired. Sign in again.");
      return false;
    }
    setIsDeleting(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      await deleteBotDetail(accessToken, botId);
      setBot(null);
      return true;
    } catch (error) {
      setSaveError(parseApiErrorMessage(error));
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  return {
    status,
    bot,
    errorMessage,
    saveError,
    saveSuccess,
    isSaving,
    isArchiving,
    isDeleting,
    refresh: load,
    save,
    archive,
    hardDelete,
  };
}
