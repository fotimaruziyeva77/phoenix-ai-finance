"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  fetchWorkspaceLeads,
  isLeadsListUnavailableError,
  type WorkspaceLead,
} from "@/lib/api/leads";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";

export type WorkspaceLeadsStatus = "idle" | "loading" | "success" | "error";

export type UseWorkspaceLeadsResult = {
  status: WorkspaceLeadsStatus;
  leads: WorkspaceLead[];
  total: number;
  endpointUnavailable: boolean;
  errorMessage: string | null;
  refetch: () => void;
  nextCursor?: string | null;
  hasMore?: boolean;
  loadingMore?: boolean;
  loadMore?: () => void;
};

export type WorkspaceLeadsFilters = {
  status?: string;
  niche?: string;
  temperature?: string;
};

export function useWorkspaceLeads(filters: WorkspaceLeadsFilters): UseWorkspaceLeadsResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<WorkspaceLeadsStatus>("idle");
  const [leads, setLeads] = useState<WorkspaceLead[]>([]);
  const [total, setTotal] = useState(0);
  const [endpointUnavailable, setEndpointUnavailable] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const statusQ = filters.status;
  const nicheQ = filters.niche;
  const temperatureQ = filters.temperature;

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setStatus("success");
      setLeads([]);
      setTotal(0);
      setEndpointUnavailable(false);
      setErrorMessage(null);
      return;
    }

    setStatus("loading");
    setErrorMessage(null);
    setEndpointUnavailable(false);
    setNextCursor(null);
    setHasMore(false);

    try {
      const { leads: items, total: t, nextCursor: nc, hasMore: hm } = await fetchWorkspaceLeads(accessToken, {
        status: statusQ,
        niche: nicheQ,
        temperature: temperatureQ,
        limit: 50,
      });
      setLeads(items);
      setTotal(t);
      setNextCursor(nc);
      setHasMore(hm);
      setStatus("success");
    } catch (e) {
      if (isLeadsListUnavailableError(e)) {
        setLeads([]);
        setTotal(0);
        setEndpointUnavailable(true);
        setStatus("success");
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        setErrorMessage("Your session expired. Sign in again.");
      } else {
        setErrorMessage(parseApiErrorMessage(e) || "Could not load leads. Check your connection and try again.");
      }
      setLeads([]);
      setTotal(0);
      setStatus("error");
    }
  }, [accessToken, canUseAuthenticatedApi, statusQ, nicheQ, temperatureQ]);

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMore || !nextCursor) return;
    setLoadingMore(true);
    try {
      const { leads: newItems, nextCursor: nc, hasMore: hm } = await fetchWorkspaceLeads(accessToken, {
        status: statusQ,
        niche: nicheQ,
        temperature: temperatureQ,
        limit: 50,
        after: nextCursor,
      });
      setLeads((prev) => [...prev, ...newItems]);
      setNextCursor(nc);
      setHasMore(hm);
    } catch {
      // silently fail — user can retry via the button
    } finally {
      setLoadingMore(false);
    }
  }, [accessToken, hasMore, loadingMore, nextCursor, statusQ, nicheQ, temperatureQ]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  return {
    status,
    leads,
    total,
    endpointUnavailable,
    errorMessage,
    refetch: load,
    nextCursor,
    hasMore,
    loadingMore,
    loadMore,
  };
}
