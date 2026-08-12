"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  activateAdminBot,
  fetchTenantInspection,
  getAdminBot,
  suspendAdminBot,
  type AdminBotDetailDto,
} from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import { ModerationSuspendDialog } from "./moderation-suspend-dialog";
import styles from "./superadmin.module.css";

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

type Props = {
  botId: string;
};

export function SuperadminBotDetail({ botId }: Props) {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const { t } = useLanguage();
  const sb = (key: string) => String(t(`superadmin.botDetail.${key}`));
  const [row, setRow] = useState<AdminBotDetailDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [suspendOpen, setSuspendOpen] = useState(false);
  const [metrics, setMetrics] = useState<{conversations: number; leads: number; aiCalls: number; aiTokens: number} | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setError(null);
    try {
      const d = await getAdminBot(accessToken, botId);
      setRow(d);
      // Fetch owner's tenant data for this bot's metrics
      try {
        const tenant = await fetchTenantInspection(accessToken, d.owner_id);
        setMetrics({
          conversations: tenant.conversation_count,
          leads: tenant.lead_count,
          aiCalls: tenant.ai_usage.total_calls,
          aiTokens: tenant.ai_usage.total_tokens,
        });
      } catch {
        /* non-critical, ignore */
      }
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setRow(null);
    }
  }, [accessToken, botId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  const isPlatformSuspended = Boolean(row?.platform_suspended_at);

  const onSuspend = async (reason: string | null) => {
    if (!canUseAuthenticatedApi || !row) return;
    setSuspendOpen(false);
    setBusy(true);
    setToast(null);
    try {
      const next = await suspendAdminBot(accessToken, row.id, { reason: reason ?? undefined });
      setRow(next);
      setToast(sb("botSuspended"));
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const onActivate = async () => {
    if (!canUseAuthenticatedApi || !row) return;
    setBusy(true);
    setToast(null);
    setError(null);
    try {
      const next = await activateAdminBot(accessToken, row.id);
      setRow(next);
      setToast(sb("suspensionCleared"));
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!row && !error) {
    return <p className={styles.pageIntro}>{sb("loadingBot")}</p>;
  }

  if (!row) {
    return (
      <div className={styles.stack}>
        <p className={styles.errorBanner}>{error}</p>
        <Link href="/superadmin/bots" className={styles.backLink}>
          ← {sb("backToBots")}
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.stack}>
      <Link href="/superadmin/bots" className={styles.backLink}>
        ← {sb("backToBots")}
      </Link>
      {error ? <p className={styles.errorBanner}>{error}</p> : null}
      {toast ? <p className={styles.successBanner}>{toast}</p> : null}
      <dl className={styles.detailGrid}>
        <dt className={styles.detailDt}>{sb("name")}</dt>
        <dd className={styles.detailDd}>{row.name}</dd>
        <dt className={styles.detailDt}>{sb("botId")}</dt>
        <dd className={styles.detailDd}>{row.id}</dd>
        <dt className={styles.detailDt}>{sb("ownerEmail")}</dt>
        <dd className={styles.detailDd}>{row.owner_email}</dd>
        <dt className={styles.detailDt}>{sb("ownerId")}</dt>
        <dd className={styles.detailDd}>{row.owner_id}</dd>
        <dt className={styles.detailDt}>{sb("niche")}</dt>
        <dd className={styles.detailDd}>{row.niche_id}</dd>
        <dt className={styles.detailDt}>{sb("goal")}</dt>
        <dd className={styles.detailDd}>{row.goal_type}</dd>
        <dt className={styles.detailDt}>{sb("status")}</dt>
        <dd className={styles.detailDd}>{row.status}</dd>
        <dt className={styles.detailDt}>{sb("providerModel")}</dt>
        <dd className={styles.detailDd}>
          {row.provider_name}
          {row.model_name ? ` / ${row.model_name}` : ""}
        </dd>
        <dt className={styles.detailDt}>{sb("widget")}</dt>
        <dd className={styles.detailDd}>{row.widget_configured ? sb("configured") : sb("notConfigured")}</dd>
        <dt className={styles.detailDt}>{sb("telegram")}</dt>
        <dd className={styles.detailDd}>{row.telegram_connected ? sb("connected") : sb("notConnected")}</dd>
        <dt className={styles.detailDt}>{sb("platformSuspended")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.platform_suspended_at)}</dd>
        <dt className={styles.detailDt}>{sb("suspensionNote")}</dt>
        <dd className={styles.detailDd}>{row.platform_suspension_reason?.trim() ? row.platform_suspension_reason : "—"}</dd>
        <dt className={styles.detailDt}>{sb("welcome")}</dt>
        <dd className={styles.detailDd}>{row.welcome_message?.trim() ? row.welcome_message : "—"}</dd>
        <dt className={styles.detailDt}>{sb("tone")}</dt>
        <dd className={styles.detailDd}>{row.tone ?? "—"}</dd>
        <dt className={styles.detailDt}>{sb("language")}</dt>
        <dd className={styles.detailDd}>{row.language ?? "—"}</dd>
        <dt className={styles.detailDt}>{sb("description")}</dt>
        <dd className={styles.detailDd}>{row.short_description?.trim() ? row.short_description : "—"}</dd>
        <dt className={styles.detailDt}>{sb("temperature")}</dt>
        <dd className={styles.detailDd}>{row.temperature ?? "—"}</dd>
        <dt className={styles.detailDt}>{sb("maxOutputTokens")}</dt>
        <dd className={styles.detailDd}>{row.max_output_tokens ?? "—"}</dd>
        <dt className={styles.detailDt}>{sb("created")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.created_at)}</dd>
        <dt className={styles.detailDt}>{sb("updated")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.updated_at)}</dd>
      </dl>
      {metrics && (
        <>
          <h3 style={{ margin: "1.25rem 0 0.5rem", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--bf-text-muted)" }}>
            {sb("performance")}
          </h3>
          <div className={styles.cardGrid}>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("conversations")}</p>
              <p className={styles.statValue}>{metrics.conversations.toLocaleString()}</p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("leadsGenerated")}</p>
              <p className={styles.statValue}>{metrics.leads.toLocaleString()}</p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("aiCalls")}</p>
              <p className={styles.statValue}>{metrics.aiCalls.toLocaleString()}</p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("aiTokens")}</p>
              <p className={styles.statValue}>{fmtTokens(metrics.aiTokens)}</p>
            </div>
          </div>
        </>
      )}
      <div className={styles.actionsRow}>
        {isPlatformSuspended ? (
          <button type="button" className={styles.btnPrimary} disabled={busy} onClick={() => void onActivate()}>
            {sb("clearSuspension")}
          </button>
        ) : (
          <button type="button" className={styles.btnDanger} disabled={busy} onClick={() => setSuspendOpen(true)}>
            {sb("platformSuspendBot")}
          </button>
        )}
      </div>
      <ModerationSuspendDialog
        open={suspendOpen}
        title={sb("suspendBotTitle")}
        description={sb("suspendBotDesc")}
        confirmLabel={sb("suspendBotConfirm")}
        onCancel={() => setSuspendOpen(false)}
        onConfirm={(r) => void onSuspend(r)}
      />
    </div>
  );
}
