"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { buildCreateBotPayload, createBotFromWizard, type BotCreateResult } from "@/lib/api/bot-create";
import { uploadBotKnowledgePdf } from "@/lib/api/bot-knowledge";
import { ApiError } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";
import { clearDraft, loadDraftOrDefault, saveDraft } from "@/lib/create-bot-wizard/draft-storage";
import { WIZARD_STEPS } from "@/lib/create-bot-wizard/steps-config";
import type { CreateBotDraft, WizardStepMeta } from "@/lib/create-bot-wizard/types";
import { validateStep } from "@/lib/create-bot-wizard/validate-step";

export type WizardSubmitStatus = "idle" | "submitting" | "success" | "error";
export type FileUploadStatus = "idle" | "uploading" | "done" | "partial_fail";

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

export function useCreateBotWizard() {
  const { accessToken, canUseAuthenticatedApi } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [draft, setDraft] = useState<CreateBotDraft>(() => createDefaultDraft());
  const [hydrated, setHydrated] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [submitStatus, setSubmitStatus] = useState<WizardSubmitStatus>("idle");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [createdBotId, setCreatedBotId] = useState<string | null>(null);
  const [createdResult, setCreatedResult] = useState<BotCreateResult | null>(null);

  // ── Pending files (not persisted to localStorage) ──────────────────────
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [fileUploadStatus, setFileUploadStatus] = useState<FileUploadStatus>("idle");
  const [fileUploadProgress, setFileUploadProgress] = useState({ uploaded: 0, total: 0 });
  const [fileUploadErrors, setFileUploadErrors] = useState<string[]>([]);

  useEffect(() => {
    setDraft(loadDraftOrDefault());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveDraft(draft);
  }, [draft, hydrated]);

  const updateDraft = useCallback((fn: (prev: CreateBotDraft) => CreateBotDraft) => {
    setDraft(fn);
    setValidationMessage(null);
    setSubmitError(null);
  }, []);

  // ── File management ────────────────────────────────────────────────────
  const addPendingFile = useCallback(
    (file: File): { ok: boolean; reason: "not_pdf" | "too_large" | null } => {
      const isPdf =
        file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      if (!isPdf) return { ok: false, reason: "not_pdf" };
      if (file.size > MAX_FILE_SIZE) return { ok: false, reason: "too_large" };
      setPendingFiles((prev) => [...prev, file]);
      return { ok: true, reason: null };
    },
    [],
  );

  const removePendingFile = useCallback((index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // ── Navigation ─────────────────────────────────────────────────────────
  const goNext = useCallback(() => {
    const { ok, message } = validateStep(stepIndex, draft);
    if (!ok) {
      setValidationMessage(message);
      return;
    }
    setValidationMessage(null);
    setStepIndex((i) => Math.min(i + 1, WIZARD_STEPS.length - 1));
  }, [draft, stepIndex]);

  const goBack = useCallback(() => {
    setValidationMessage(null);
    setStepIndex((i) => Math.max(0, i - 1));
  }, []);

  // ── Submit + file upload ───────────────────────────────────────────────
  const submitDraft = useCallback(
    async (nextDraft: CreateBotDraft) => {
      if (!canUseAuthenticatedApi) {
        setSubmitStatus("error");
        setSubmitError("You are not authenticated. Please sign in and try again.");
        return;
      }
      setSubmitStatus("submitting");
      setSubmitError(null);
      saveDraft(nextDraft);
      const payload = buildCreateBotPayload(nextDraft);
      try {
        const created = await createBotFromWizard(accessToken, payload);
        setCreatedBotId(created.id);
        setCreatedResult(created);
        clearDraft();
        setSubmitStatus("success");

        // Upload pending PDF files after bot creation
        if (pendingFiles.length > 0) {
          setFileUploadStatus("uploading");
          setFileUploadProgress({ uploaded: 0, total: pendingFiles.length });
          const errors: string[] = [];

          for (let i = 0; i < pendingFiles.length; i++) {
            const file = pendingFiles[i];
            if (!file) continue;
            try {
              await uploadBotKnowledgePdf(accessToken, created.id, file);
            } catch {
              errors.push(file.name);
            }
            setFileUploadProgress({ uploaded: i + 1, total: pendingFiles.length });
          }

          setFileUploadErrors(errors);
          setFileUploadStatus(errors.length > 0 ? "partial_fail" : "done");
          setPendingFiles([]);
        }
      } catch (error) {
        setSubmitStatus("error");
        if (error instanceof ApiError) {
          if (error.status === 401) {
            setSubmitError("Your session expired. Please sign in and try again.");
            return;
          }
          if (error.status === 422 || error.status === 409 || error.status === 502 || error.status === 503) {
            setSubmitError(parseApiErrorMessage(error));
            return;
          }
          if (error.status === 403) {
            setSubmitError("You are not allowed to create bots in this workspace.");
            return;
          }
          setSubmitError("Could not create bot right now. Please try again.");
          return;
        }
        setSubmitError("Unexpected error while creating bot. Please try again.");
      }
    },
    [accessToken, canUseAuthenticatedApi, pendingFiles],
  );

  const isLastStep = stepIndex === WIZARD_STEPS.length - 1;

  const skipCurrent = useCallback(async () => {
    const meta = WIZARD_STEPS[stepIndex];
    if (!meta?.skippable) return;
    const nextDraft = meta.applySkip ? meta.applySkip(draft) : draft;
    setDraft(nextDraft);
    setValidationMessage(null);
    setSubmitError(null);
    if (isLastStep) {
      await submitDraft(nextDraft);
      return;
    }
    setStepIndex((i) => Math.min(i + 1, WIZARD_STEPS.length - 1));
  }, [draft, isLastStep, stepIndex, submitDraft]);

  const finish = useCallback(async () => {
    const { ok, message } = validateStep(stepIndex, draft);
    if (!ok) {
      setValidationMessage(message);
      return;
    }
    await submitDraft(draft);
  }, [draft, stepIndex, submitDraft]);

  const resetWizard = useCallback(() => {
    clearDraft();
    setDraft(createDefaultDraft());
    setStepIndex(0);
    setSubmitStatus("idle");
    setSubmitError(null);
    setCreatedBotId(null);
    setCreatedResult(null);
    setValidationMessage(null);
    setPendingFiles([]);
    setFileUploadStatus("idle");
    setFileUploadProgress({ uploaded: 0, total: 0 });
    setFileUploadErrors([]);
  }, []);

  const fallback = WIZARD_STEPS[0];
  if (!fallback) {
    throw new Error("WIZARD_STEPS must not be empty");
  }
  const currentStep: WizardStepMeta = WIZARD_STEPS[stepIndex] ?? fallback;

  return {
    stepIndex,
    currentStep,
    draft,
    updateDraft,
    validationMessage,
    submitStatus,
    submitError,
    createdBotId,
    createdResult,
    hydrated,
    goNext,
    goBack,
    skipCurrent,
    finish,
    resetWizard,
    isLastStep,
    // File upload
    pendingFiles,
    addPendingFile,
    removePendingFile,
    fileUploadStatus,
    fileUploadProgress,
    fileUploadErrors,
  };
}
