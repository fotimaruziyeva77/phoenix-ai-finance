"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import {
  fetchLeadDetail,
  patchLeadPipeline,
  type LeadDetail,
  type LeadPipelineFormPayload,
} from "@/lib/api/lead-detail";

type LeadDetailLoadStatus = "idle" | "loading" | "success" | "error";

export type UseLeadDetailResult = {
  status: LeadDetailLoadStatus;
  lead: LeadDetail | null;
  errorMessage: string | null;
  saveError: string | null;
  saveSuccess: string | null;
  isSaving: boolean;
  refresh: () => void;
  savePipeline: (payload: LeadPipelineFormPayload) => Promise<boolean>;
};

export function useLeadDetail(leadId: string): UseLeadDetailResult {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [status, setStatus] = useState<LeadDetailLoadStatus>("idle");
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) {
      setStatus("error");
      setErrorMessage("Your session expired. Sign in again.");
      setLead(null);
      return;
    }
    setStatus("loading");
    setErrorMessage(null);
    try {
      const next = await fetchLeadDetail(accessToken, leadId);
      setLead(next);
      setStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setErrorMessage("Lead not found.");
      } else if (error instanceof ApiError && error.status === 401) {
        setErrorMessage("Your session expired. Sign in again.");
      } else {
        setErrorMessage(parseApiErrorMessage(error) || "Could not load this lead.");
      }
      setLead(null);
      setStatus("error");
    }
  }, [accessToken, leadId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated) return;
    void load();
  }, [hydrated, load]);

  useEffect(() => {
    if (!saveSuccess) return;
    const t = setTimeout(() => setSaveSuccess(null), 2800);
    return () => clearTimeout(t);
  }, [saveSuccess]);

  const savePipeline = useCallback(
    async (payload: LeadPipelineFormPayload) => {
      if (!canUseAuthenticatedApi) {
        setSaveError("Your session expired. Sign in again.");
        setSaveSuccess(null);
        return false;
      }
      setIsSaving(true);
      setSaveError(null);
      setSaveSuccess(null);
      try {
        const next = await patchLeadPipeline(accessToken, leadId, payload);
        setLead(next);
        setSaveSuccess("Saved.");
        return true;
      } catch (error) {
        setSaveSuccess(null);
        if (error instanceof ApiError && error.status === 409) {
          setSaveError(parseApiErrorMessage(error));
        } else if (error instanceof ApiError && error.status === 422) {
          setSaveError(parseApiErrorMessage(error));
        } else if (error instanceof ApiError && error.status === 401) {
          setSaveError("Your session expired. Sign in again.");
        } else {
          setSaveError(parseApiErrorMessage(error) || "Could not save changes.");
        }
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [accessToken, leadId, canUseAuthenticatedApi],
  );

  return {
    status,
    lead,
    errorMessage,
    saveError,
    saveSuccess,
    isSaving,
    refresh: load,
    savePipeline,
  };
}
