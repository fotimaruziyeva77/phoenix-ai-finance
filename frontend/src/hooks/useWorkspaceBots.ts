"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { fetchWorkspaceBots, isBotsListUnavailableError, type WorkspaceBot } from "@/lib/api/bots";
import { ApiError } from "@/lib/api/client";

export type WorkspaceBotsStatus = "idle" | "loading" | "success" | "error";

export type UseWorkspaceBotsResult = {
  status: WorkspaceBotsStatus;
  bots: WorkspaceBot[];
  /** True when the route is not deployed yet (404). UI can still show empty state. */
  endpointUnavailable: boolean;
  errorMessage: string | null;
  refetch: () => void;
};

export function useWorkspaceBots(): UseWorkspaceBotsResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<WorkspaceBotsStatus>("idle");
  const [bots, setBots] = useState<WorkspaceBot[]>([]);
  const [endpointUnavailable, setEndpointUnavailable] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setStatus("success");
      setBots([]);
      setEndpointUnavailable(false);
      setErrorMessage(null);
      return;
    }

    setStatus("loading");
    setErrorMessage(null);
    setEndpointUnavailable(false);

    try {
      const items = await fetchWorkspaceBots(accessToken);
      setBots(items);
      setStatus("success");
    } catch (e) {
      if (isBotsListUnavailableError(e)) {
        setBots([]);
        setEndpointUnavailable(true);
        setStatus("success");
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        setErrorMessage("Your session expired. Sign in again.");
      } else {
        setErrorMessage("Could not load bots. Check your connection and try again.");
      }
      setBots([]);
      setStatus("error");
    }
  }, [accessToken, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  return {
    status,
    bots,
    endpointUnavailable,
    errorMessage,
    refetch: load,
  };
}
