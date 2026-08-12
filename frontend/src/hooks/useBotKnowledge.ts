"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { fetchBotKnowledgeFiles, uploadBotKnowledgePdf, type KnowledgeFileListItemDto } from "@/lib/api/bot-knowledge";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { knowledgeListNeedsPolling } from "@/lib/knowledge-domain/polling";

type Status = "idle" | "loading" | "success" | "error";

const POLL_MS = 4000;

export function useBotKnowledge(botId: string) {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<Status>("idle");
  const [items, setItems] = useState<KnowledgeFileListItemDto[]>([]);
  const [total, setTotal] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const load = useCallback(async (soft = false) => {
    if (!canUseAuthenticatedApi) {
      setStatus("error");
      setLoadError("Your session expired. Sign in again.");
      setItems([]);
      setTotal(0);
      return;
    }
    setLoadError(null);
    if (!soft) {
      setStatus("loading");
    }
    try {
      const res = await fetchBotKnowledgeFiles(accessToken, botId);
      setItems(res.items);
      setTotal(res.total);
      setStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setLoadError("Bot not found.");
      } else if (error instanceof ApiError && error.status === 403) {
        setLoadError("You do not have access to this bot.");
      } else if (error instanceof ApiError && error.status === 401) {
        setLoadError("Your session expired. Sign in again.");
      } else {
        setLoadError("Could not load knowledge files.");
      }
      setItems([]);
      setTotal(0);
      setStatus("error");
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated) return;
    setStatus("idle");
    setItems([]);
    setTotal(0);
    setLoadError(null);
    void load(false);
  }, [hydrated, botId, accessToken, canUseAuthenticatedApi, load]);

  useEffect(() => {
    if (status !== "success") {
      stopPoll();
      return;
    }
    if (knowledgeListNeedsPolling(items)) {
      if (pollRef.current === null) {
        pollRef.current = setInterval(() => {
          void load(true);
        }, POLL_MS);
      }
    } else {
      stopPoll();
    }
    return () => {
      stopPoll();
    };
  }, [status, items, load, stopPoll]);

  const refresh = useCallback(() => {
    void load(false);
  }, [load]);

  const upload = useCallback(
    async (file: File) => {
      if (!canUseAuthenticatedApi) {
        setUploadError("Your session expired. Sign in again.");
        return;
      }
      setUploadError(null);
      setIsUploading(true);
      try {
        await uploadBotKnowledgePdf(accessToken, botId, file);
        await load(true);
      } catch (error) {
        setUploadError(parseApiErrorMessage(error));
      } finally {
        setIsUploading(false);
      }
    },
    [accessToken, botId, load, canUseAuthenticatedApi],
  );

  return {
    status,
    items,
    total,
    loadError,
    uploadError,
    isUploading,
    refresh,
    upload,
    clearUploadError: () => setUploadError(null),
  };
}
