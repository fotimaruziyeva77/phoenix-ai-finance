"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useCreateBotWizard } from "@/hooks/useCreateBotWizard";

import { WizardNavigation } from "./wizard-navigation";
import { WizardStepper } from "./wizard-stepper";
import { StepBasics } from "./steps/step-basics";
import { StepChannel } from "./steps/step-channel";
import { StepGoal } from "./steps/step-goal";
import { StepKnowledge } from "./steps/step-knowledge";
import { StepNiche } from "./steps/step-niche";
import { StepReview } from "./steps/step-review";
import styles from "./create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

const STEP_TITLE_KEYS: Record<string, string> = {
  niche: "dashboard.wizard.nicheTitle",
  goal: "dashboard.wizard.goalTitle",
  basics: "dashboard.wizard.basicsTitle",
  channel: "dashboard.wizard.channelTitle",
  knowledge: "dashboard.wizard.knowledgeTitle",
  review: "dashboard.wizard.reviewTitle",
};
const STEP_DESC_KEYS: Record<string, string> = {
  niche: "dashboard.wizard.nicheDesc",
  goal: "dashboard.wizard.goalDesc",
  basics: "dashboard.wizard.basicsDesc",
  channel: "dashboard.wizard.channelDesc",
  knowledge: "dashboard.wizard.knowledgeDesc",
  review: "dashboard.wizard.reviewDesc",
};

function completionCopy(status: string, t: TFn): { title: string; body: string } {
  if (status === "active") {
    return {
      title: t("dashboard.wizard.doneActiveTitle") as string,
      body: t("dashboard.wizard.doneActiveBody") as string,
    };
  }
  if (status === "channel_pending") {
    return {
      title: t("dashboard.wizard.donePendingTitle") as string,
      body: t("dashboard.wizard.donePendingBody") as string,
    };
  }
  return {
    title: t("dashboard.wizard.doneDefaultTitle") as string,
    body: t("dashboard.wizard.doneDefaultBody") as string,
  };
}

export function CreateBotWizard() {
  const {
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
    isLastStep,
    // File upload
    pendingFiles,
    addPendingFile,
    removePendingFile,
    fileUploadStatus,
    fileUploadProgress,
    fileUploadErrors,
  } = useCreateBotWizard();
  const { t } = useLanguage();
  const router = useRouter();

  // Auto-redirect after success — wait for file uploads to finish
  useEffect(() => {
    if (submitStatus !== "success") return;
    // If files are still uploading, don't redirect yet
    if (fileUploadStatus === "uploading") return;

    const timer = window.setTimeout(() => {
      const target = createdBotId
        ? `/dashboard/bots?created=${encodeURIComponent(createdBotId)}`
        : "/dashboard/bots";
      router.push(target);
    }, 2800);
    return () => window.clearTimeout(timer);
  }, [createdBotId, router, submitStatus, fileUploadStatus]);

  if (!hydrated) {
    return (
      <div className={`${styles.shell} bf-main--narrow`} aria-busy="true" data-testid="create-bot-wizard-loading">
        <p className={styles.lead}>{t("dashboard.wizard.loading") as string}</p>
      </div>
    );
  }

  if (submitStatus === "success" && createdResult) {
    const { title, body } = completionCopy(createdResult.status, t);
    return (
      <div className={`${styles.shell} bf-main--narrow`} data-testid="create-bot-wizard">
        <div
          className={styles.completion}
          data-testid="wizard-submitting-success"
          data-created-status={createdResult.status}
        >
          <h2 className={styles.completionTitle}>{title}</h2>
          <p className={styles.completionBody}>{body}</p>
          <p className={styles.completionBody} data-testid="wizard-success-status-line">
            {t("dashboard.wizard.serverStatus") as string} <strong>{createdResult.status}</strong>
            {createdResult.primary_channel ? (
              <>
                {" "}
                · {t("dashboard.wizard.primaryChannel") as string} <strong>{createdResult.primary_channel}</strong>
              </>
            ) : null}
          </p>

          {/* ── File upload progress ──────────────────────── */}
          {fileUploadStatus === "uploading" && (
            <div className={styles.uploadProgress} data-testid="wizard-upload-progress">
              <p className={styles.uploadProgressText}>
                {t("dashboard.wizard.uploadingFiles") as string}{" "}
                ({fileUploadProgress.uploaded}/{fileUploadProgress.total})
              </p>
              <div className={styles.uploadProgressBar}>
                <div
                  className={styles.uploadProgressFill}
                  style={{
                    width: `${fileUploadProgress.total > 0 ? (fileUploadProgress.uploaded / fileUploadProgress.total) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}

          {fileUploadStatus === "done" && (
            <div className={styles.uploadSuccess} data-testid="wizard-upload-done">
              {t("dashboard.wizard.uploadComplete") as string}
            </div>
          )}

          {fileUploadStatus === "partial_fail" && (
            <div className={styles.uploadFail} data-testid="wizard-upload-fail">
              <p>{t("dashboard.wizard.uploadPartialFail") as string}</p>
              {fileUploadErrors.length > 0 && (
                <p style={{ marginTop: "0.35rem", fontSize: "0.75rem" }}>
                  {fileUploadErrors.join(", ")}
                </p>
              )}
            </div>
          )}

          <div className={styles.completionActions}>
            <Link href="/dashboard/bots" className={styles.completionLink}>
              {t("dashboard.wizard.openBots") as string}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.shell} bf-main--narrow`} data-testid="create-bot-wizard">
      <div className={styles.topBar}>
        <h1 className={styles.pageTitle}>{t("dashboard.wizard.title") as string}</h1>
      </div>

      <p className={styles.lead}>
        {t("dashboard.wizard.lead") as string}
      </p>

      <p className={styles.wizardAssistiveHint} data-testid="wizard-assistive-hint">
        {t("dashboard.wizard.assistiveHint") as string}
      </p>

      <WizardStepper stepIndex={stepIndex} t={t} />

      <div className={styles.panel} data-testid={`wizard-step-${currentStep.id}`}>
        <h2 className={styles.stepTitle}>{t(STEP_TITLE_KEYS[currentStep.id] ?? "") as string}</h2>
        <p className={styles.stepDesc}>{t(STEP_DESC_KEYS[currentStep.id] ?? "") as string}</p>

        {validationMessage ? (
          <p className={styles.error} role="alert" data-testid="wizard-step-error">
            {validationMessage}
          </p>
        ) : null}
        {submitError ? (
          <p className={styles.error} role="alert" data-testid="wizard-submit-error">
            {submitError}
          </p>
        ) : null}

        {currentStep.id === "niche" ? <StepNiche draft={draft} updateDraft={updateDraft} t={t} /> : null}
        {currentStep.id === "goal" ? <StepGoal draft={draft} updateDraft={updateDraft} t={t} /> : null}
        {currentStep.id === "basics" ? <StepBasics draft={draft} updateDraft={updateDraft} t={t} /> : null}
        {currentStep.id === "channel" ? <StepChannel draft={draft} updateDraft={updateDraft} t={t} /> : null}
        {currentStep.id === "knowledge" ? (
          <StepKnowledge
            draft={draft}
            updateDraft={updateDraft}
            t={t}
            pendingFiles={pendingFiles}
            onAddFile={addPendingFile}
            onRemoveFile={removePendingFile}
          />
        ) : null}
        {currentStep.id === "review" ? (
          <StepReview draft={draft} t={t} pendingFilesCount={pendingFiles.length} />
        ) : null}
      </div>

      <WizardNavigation
        stepIndex={stepIndex}
        isLastStep={isLastStep}
        skippable={currentStep.skippable}
        isSubmitting={submitStatus === "submitting"}
        onBack={goBack}
        onNext={goNext}
        onSkip={skipCurrent}
        onFinish={finish}
        t={t}
      />
    </div>
  );
}
