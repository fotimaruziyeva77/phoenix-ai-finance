"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useLeadDetail } from "@/hooks/useLeadDetail";
import type { LeadDetail } from "@/lib/api/lead-detail";
import type { LeadPipelineStatus, LeadTemperature } from "@/lib/api/leads";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import { LeadPipelineBadge } from "./lead-pipeline-badge";
import { LeadTemperatureBadge } from "./lead-temperature-badge";
import styles from "./lead-detail.module.css";

type Props = {
  leadId: string;
};

function pageHeading(lead: LeadDetail): string {
  if (lead.name) return lead.name;
  const s = lead.summary?.trim();
  if (s) {
    const line = s.split(/\n/)[0]?.trim() ?? "";
    if (line.length > 72) return `${line.slice(0, 69)}…`;
    return line || "Lead";
  }
  return "Lead";
}

type PipelineForm = {
  status: LeadPipelineStatus;
  temperature: LeadTemperature | "";
  notes: string;
  assigneeUserId: string;
};

function toPipelineForm(lead: LeadDetail): PipelineForm {
  return {
    status: lead.status,
    temperature: lead.temperature ?? "",
    notes: lead.notes ?? "",
    assigneeUserId: lead.assigneeUserId ?? "",
  };
}

export function LeadDetailPage({ leadId }: Props) {
  const { t } = useLanguage();
  const { status, lead, errorMessage, saveError, saveSuccess, isSaving, refresh, savePipeline } =
    useLeadDetail(leadId);

  const [form, setForm] = useState<PipelineForm | null>(null);

  useEffect(() => {
    if (lead) {
      setForm(toPipelineForm(lead));
    }
  }, [lead]);

  const collectedPretty = useMemo(() => {
    if (!lead?.collectedData || Object.keys(lead.collectedData).length === 0) return null;
    try {
      return JSON.stringify(lead.collectedData, null, 2);
    } catch {
      return String(lead.collectedData);
    }
  }, [lead]);

  const pipelineOptions = [
    { value: "new" as LeadPipelineStatus, labelKey: "dashboard.leads.stNew" },
    { value: "contacted" as LeadPipelineStatus, labelKey: "dashboard.leads.stContacted" },
    { value: "qualified" as LeadPipelineStatus, labelKey: "dashboard.leads.stQualified" },
    { value: "proposal" as LeadPipelineStatus, labelKey: "dashboard.leads.stProposal" },
    { value: "won" as LeadPipelineStatus, labelKey: "dashboard.leads.stWon" },
    { value: "lost" as LeadPipelineStatus, labelKey: "dashboard.leads.stLost" },
  ];

  const tempOptions: { value: LeadTemperature | ""; labelKey: string }[] = [
    { value: "", labelKey: "dashboard.leads.detailNoTemp" },
    { value: "cold", labelKey: "dashboard.leads.tempCold" },
    { value: "warm", labelKey: "dashboard.leads.tempWarm" },
    { value: "hot", labelKey: "dashboard.leads.tempHot" },
  ];

  if (status === "loading" || status === "idle") {
    return <p className={styles.rowMeta}>{t("dashboard.leads.detailLoading") as string}</p>;
  }

  if (status === "error" || !lead) {
    return (
      <div className={styles.stack}>
        <Link href="/dashboard/leads" className={styles.backLink}>
          ← {t("dashboard.leads.detailBack") as string}
        </Link>
        <p className={styles.errorBanner} data-testid="lead-detail-load-error" role="alert">
          {errorMessage ?? (t("dashboard.leads.detailLoadError") as string)}
        </p>
        <div className={styles.actions}>
          <button type="button" className={styles.saveBtn} onClick={() => void refresh()}>
            {t("dashboard.leads.retry") as string}
          </button>
        </div>
      </div>
    );
  }

  const heading = pageHeading(lead);
  const activeForm = form ?? toPipelineForm(lead);

  const setField = (patch: Partial<PipelineForm>) => {
    setForm((f) => {
      const base = f ?? toPipelineForm(lead);
      return { ...base, ...patch };
    });
  };

  const onSave = async () => {
    await savePipeline({
      status: activeForm.status,
      lead_temperature: activeForm.temperature === "" ? null : activeForm.temperature,
      notes: activeForm.notes.trim() ? activeForm.notes.trim() : null,
      assignee_user_id: activeForm.assigneeUserId.trim() ? activeForm.assigneeUserId.trim() : null,
    });
  };

  return (
    <div className={styles.stack} data-testid="lead-detail-root">
      <div className={styles.headerRow}>
        <div className={styles.titleBlock}>
          <h1 className={styles.title}>{heading}</h1>
          <p className={styles.meta}>
            {t("dashboard.leads.colNiche") as string}: {lead.nicheLabel}
            {lead.leadScore !== null ? ` · ${t("dashboard.leads.colScore") as string} ${lead.leadScore}` : ""}
          </p>
        </div>
        <Link href="/dashboard/leads" className={styles.backLink}>
          ← {t("dashboard.leads.detailBack") as string}
        </Link>
      </div>

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{t("dashboard.leads.detailSummary") as string}</h2>
            {lead.summary?.trim() ? (
              <p className={styles.summaryText}>{lead.summary.trim()}</p>
            ) : (
              <p className={styles.muted}>{t("dashboard.leads.detailSummaryEmpty") as string}</p>
            )}
          </section>

          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{t("dashboard.leads.detailCollected") as string}</h2>
            {collectedPretty ? (
              <pre className={styles.jsonBlock}>{collectedPretty}</pre>
            ) : (
              <p className={styles.muted}>{t("dashboard.leads.detailCollectedEmpty") as string}</p>
            )}
          </section>

          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{t("dashboard.leads.detailDetails") as string}</h2>
            <div className={styles.metaGrid}>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.detailCurrentStatus") as string}</div>
                <div className={styles.badgeRow}>
                  <LeadPipelineBadge status={lead.status} />
                </div>
              </div>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.temperature") as string}</div>
                <div className={styles.badgeRow}>
                  <LeadTemperatureBadge temperature={lead.temperature} />
                </div>
              </div>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.detailPhone") as string}</div>
                <p className={styles.fieldValue}>{lead.phone ?? "—"}</p>
              </div>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.detailSource") as string}</div>
                <p className={styles.fieldValue}>{lead.sourceChannel ?? "—"}</p>
              </div>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.detailCreated") as string}</div>
                <p className={styles.fieldValue}>{formatDashboardDateTime(lead.createdAt)}</p>
              </div>
              <div>
                <div className={styles.fieldLabel}>{t("dashboard.leads.detailUpdated") as string}</div>
                <p className={styles.fieldValue}>{formatDashboardDateTime(lead.updatedAt)}</p>
              </div>
            </div>
          </section>
        </div>

        <aside className={styles.sideColumn}>
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>{t("dashboard.leads.detailPipeline") as string}</h2>
            <p className={styles.hint}>{t("dashboard.leads.detailPipelineHint") as string}</p>

            {saveError ? (
              <p className={styles.errorBanner} role="alert" data-testid="lead-detail-save-error">
                {saveError}
              </p>
            ) : null}
            {saveSuccess ? (
              <p className={styles.successBanner} data-testid="lead-detail-save-success">
                {saveSuccess}
              </p>
            ) : null}

            <div className={styles.formStack}>
              <div>
                <label className={styles.fieldLabel} htmlFor="lead-pipeline-status">
                  {t("dashboard.leads.colStatus") as string}
                </label>
                <select
                  id="lead-pipeline-status"
                  className={styles.select}
                  value={activeForm.status}
                  onChange={(e) => setField({ status: e.target.value as LeadPipelineStatus })}
                >
                  {pipelineOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {t(o.labelKey) as string}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={styles.fieldLabel} htmlFor="lead-pipeline-temp">
                  {t("dashboard.leads.temperature") as string}
                </label>
                <select
                  id="lead-pipeline-temp"
                  className={styles.select}
                  value={activeForm.temperature}
                  onChange={(e) => setField({ temperature: e.target.value as LeadTemperature | "" })}
                >
                  {tempOptions.map((o) => (
                    <option key={o.value || "none"} value={o.value}>
                      {t(o.labelKey) as string}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={styles.fieldLabel} htmlFor="lead-pipeline-notes">
                  {t("dashboard.leads.detailNotes") as string}
                </label>
                <textarea
                  id="lead-pipeline-notes"
                  className={styles.textarea}
                  value={activeForm.notes}
                  onChange={(e) => setField({ notes: e.target.value })}
                  placeholder={t("dashboard.leads.detailNotesPlaceholder") as string}
                  maxLength={16000}
                />
              </div>
              <div>
                <label className={styles.fieldLabel} htmlFor="lead-pipeline-assignee">
                  {t("dashboard.leads.detailAssignee") as string}
                </label>
                <input
                  id="lead-pipeline-assignee"
                  type="text"
                  className={styles.select}
                  value={activeForm.assigneeUserId}
                  onChange={(e) => setField({ assigneeUserId: e.target.value })}
                  placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                  maxLength={36}
                />
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.saveBtn}
                  disabled={isSaving}
                  onClick={() => void onSave()}
                  data-testid="lead-detail-save"
                >
                  {isSaving
                    ? (t("dashboard.leads.detailSaving") as string)
                    : (t("dashboard.leads.detailSave") as string)}
                </button>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
