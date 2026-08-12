"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  activateAdminUser,
  adminOverrideSubscription,
  getAdminUser,
  impersonateUser,
  suspendAdminUser,
  type AdminUserDetailDto,
} from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import { ModerationSuspendDialog } from "./moderation-suspend-dialog";
import styles from "./superadmin.module.css";

type Props = {
  userId: string;
};

export function SuperadminUserDetail({ userId }: Props) {
  const { accessToken, hydrated, canUseAuthenticatedApi, user: me, refreshProfile } = useAuth();
  const { t } = useLanguage();
  const sd = (key: string) => String(t(`superadmin.userDetail.${key}`));
  const [row, setRow] = useState<AdminUserDetailDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [suspendOpen, setSuspendOpen] = useState(false);

  const [overridePlan, setOverridePlan] = useState<string>("free");
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [overrideBusy, setOverrideBusy] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [overrideToast, setOverrideToast] = useState<string | null>(null);

  const [impersonateBusy, setImpersonateBusy] = useState(false);
  const [impersonateToken, setImpersonateToken] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setError(null);
    try {
      const d = await getAdminUser(accessToken, userId);
      setRow(d);
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setRow(null);
    }
  }, [accessToken, userId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  const isSuspended = Boolean(row && (!row.is_active || row.suspended_at));

  const onSuspend = async (reason: string | null) => {
    if (!canUseAuthenticatedApi || !row) return;
    setSuspendOpen(false);
    setBusy(true);
    setToast(null);
    try {
      const next = await suspendAdminUser(accessToken, row.id, { reason: reason ?? undefined });
      setRow(next);
      setToast(sd("userSuspended"));
      if (me?.id === row.id) await refreshProfile();
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const onOverrideSubscription = async () => {
    if (!canUseAuthenticatedApi || !row) return;
    setOverrideBusy(true);
    setOverrideError(null);
    setOverrideToast(null);
    try {
      await adminOverrideSubscription(accessToken, row.id, overridePlan, overrideReason.trim() || undefined);
      setOverrideToast(sd("planOverridden"));
      setOverrideReason("");
    } catch (e) {
      setOverrideError(parseApiErrorMessage(e));
    } finally {
      setOverrideBusy(false);
    }
  };

  const onImpersonate = async () => {
    if (!canUseAuthenticatedApi || !row) return;
    setImpersonateBusy(true);
    setError(null);
    try {
      const res = await impersonateUser(accessToken, row.id);
      setImpersonateToken(res.access_token);
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setImpersonateBusy(false);
    }
  };

  const onActivate = async () => {
    if (!canUseAuthenticatedApi || !row) return;
    setBusy(true);
    setToast(null);
    setError(null);
    try {
      const next = await activateAdminUser(accessToken, row.id);
      setRow(next);
      setToast(sd("userActivated"));
      if (me?.id === row.id) await refreshProfile();
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (!row && !error) {
    return <p className={styles.pageIntro}>{sd("loadingUser")}</p>;
  }

  if (!row) {
    return (
      <div className={styles.stack}>
        <p className={styles.errorBanner}>{error}</p>
        <Link href="/superadmin/users" className={styles.backLink}>
          ← {sd("backToUsers")}
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.stack}>
      <Link href="/superadmin/users" className={styles.backLink}>
        ← {sd("backToUsers")}
      </Link>
      <p className={styles.pageIntro}>
        <Link href={`/superadmin/users/${row.id}/inspect`} className={`${styles.btn} ${styles.btnNeutral}`}>
          {sd("inspectTenant")}
        </Link>
      </p>
      {error ? <p className={styles.errorBanner}>{error}</p> : null}
      {toast ? <p className={styles.successBanner}>{toast}</p> : null}
      <dl className={styles.detailGrid}>
        <dt className={styles.detailDt}>{sd("email")}</dt>
        <dd className={styles.detailDd}>{row.email}</dd>
        <dt className={styles.detailDt}>{sd("name")}</dt>
        <dd className={styles.detailDd}>{row.full_name ?? "—"}</dd>
        <dt className={styles.detailDt}>{sd("role")}</dt>
        <dd className={styles.detailDd}>{row.role}</dd>
        <dt className={styles.detailDt}>{sd("active")}</dt>
        <dd className={styles.detailDd}>{row.is_active ? sd("yes") : sd("no")}</dd>
        <dt className={styles.detailDt}>{sd("verified")}</dt>
        <dd className={styles.detailDd}>{row.is_verified ? sd("yes") : sd("no")}</dd>
        <dt className={styles.detailDt}>{sd("password")}</dt>
        <dd className={styles.detailDd}>{row.has_password ? sd("set") : sd("notSet")}</dd>
        <dt className={styles.detailDt}>{sd("suspendedAt")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.suspended_at)}</dd>
        <dt className={styles.detailDt}>{sd("suspensionNote")}</dt>
        <dd className={styles.detailDd}>{row.suspension_reason?.trim() ? row.suspension_reason : "—"}</dd>
        <dt className={styles.detailDt}>{sd("oauthProviders")}</dt>
        <dd className={styles.detailDd}>
          {row.oauth_providers.length ? row.oauth_providers.map((p) => p.provider).join(", ") : "—"}
        </dd>
        <dt className={styles.detailDt}>{sd("bots")}</dt>
        <dd className={styles.detailDd}>{row.bot_count}</dd>
        <dt className={styles.detailDt}>{sd("created")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.created_at)}</dd>
        <dt className={styles.detailDt}>{sd("updated")}</dt>
        <dd className={styles.detailDd}>{formatDashboardDateTime(row.updated_at)}</dd>
      </dl>
      <div className={styles.actionsRow}>
        {isSuspended ? (
          <button type="button" className={styles.btnPrimary} disabled={busy} onClick={() => void onActivate()}>
            {sd("activateUser")}
          </button>
        ) : me?.id === row.id ? (
          <p className={styles.pageIntro}>{sd("cannotSuspendSelf")}</p>
        ) : (
          <button type="button" className={styles.btnDanger} disabled={busy} onClick={() => setSuspendOpen(true)}>
            {sd("suspendUser")}
          </button>
        )}
      </div>
      {/* Impersonation */}
      {me?.id !== row.id && row.role !== "superadmin" && (
        <div className={styles.actionsRow} style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.5rem" }}>
          <p className={styles.pageIntro} style={{ marginBottom: "0.1rem", fontWeight: 600, color: "var(--bf-text)" }}>
            {sd("impersonation")}
          </p>
          <p className={styles.pageIntro}>{sd("impersonationDesc")}</p>
          <button
            type="button"
            className={`${styles.btn} ${styles.btnNeutral}`}
            disabled={impersonateBusy}
            onClick={() => void onImpersonate()}
          >
            {impersonateBusy ? sd("generating") : sd("generateToken")}
          </button>
          {impersonateToken && (
            <div style={{ marginTop: "0.35rem", padding: "0.6rem 0.75rem", borderRadius: "9px", border: "1px solid color-mix(in srgb, var(--bf-border) 70%, transparent)", background: "var(--bf-page-bg)", maxWidth: "100%", overflow: "auto" }}>
              <p style={{ margin: "0 0 0.35rem", fontSize: "0.75rem", color: "var(--bf-text-muted)", fontWeight: 600 }}>
                {sd("tokenHint")}
              </p>
              <code style={{ fontSize: "0.7rem", wordBreak: "break-all", color: "var(--bf-accent-soft)" }}>{impersonateToken}</code>
              <div style={{ marginTop: "0.35rem", display: "flex", gap: "0.5rem" }}>
                <button className={styles.btnNeutral} style={{ fontSize: "0.75rem", padding: "3px 10px" }} onClick={() => { void navigator.clipboard.writeText(impersonateToken); }}>{sd("copy")}</button>
                <button className={styles.btnNeutral} style={{ fontSize: "0.75rem", padding: "3px 10px" }} onClick={() => setImpersonateToken(null)}>{sd("dismiss")}</button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className={styles.actionsRow} style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.65rem" }}>
        <p className={styles.pageIntro} style={{ marginBottom: "0.25rem", fontWeight: 600, color: "var(--bf-text)" }}>
          {sd("planOverride")}
        </p>
        {overrideError ? <p className={styles.errorBanner}>{overrideError}</p> : null}
        {overrideToast ? <p className={styles.successBanner}>{overrideToast}</p> : null}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "flex-end", width: "100%", maxWidth: "30rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: "0 0 auto" }}>
            <label htmlFor="plan-override-select" className={styles.detailDt} style={{ fontSize: "0.75rem" }}>
              {sd("plan")}
            </label>
            <select
              id="plan-override-select"
              value={overridePlan}
              onChange={(e) => setOverridePlan(e.target.value)}
              disabled={overrideBusy}
              style={{ minHeight: "2.1rem", borderRadius: "9px", border: "1px solid color-mix(in srgb, var(--bf-border) 80%, transparent)", background: "var(--bf-page-bg)", color: "var(--bf-text)", fontSize: "0.8125rem", padding: "0.3rem 0.55rem" }}
            >
              <option value="free">free</option>
              <option value="pro">pro</option>
              <option value="business">business</option>
              <option value="enterprise">enterprise</option>
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", flex: "1 1 10rem" }}>
            <label htmlFor="plan-override-reason" className={styles.detailDt} style={{ fontSize: "0.75rem" }}>
              {sd("reasonOptional")}
            </label>
            <input
              id="plan-override-reason"
              type="text"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              disabled={overrideBusy}
              placeholder={sd("reasonPlaceholder")}
              style={{ minHeight: "2.1rem", borderRadius: "9px", border: "1px solid color-mix(in srgb, var(--bf-border) 80%, transparent)", background: "var(--bf-page-bg)", color: "var(--bf-text)", fontSize: "0.8125rem", padding: "0.3rem 0.55rem" }}
            />
          </div>
          <button
            type="button"
            className={`${styles.btn} ${styles.btnNeutral}`}
            disabled={overrideBusy}
            onClick={() => void onOverrideSubscription()}
          >
            {overrideBusy ? sd("applying") : sd("applyOverride")}
          </button>
        </div>
      </div>
      <ModerationSuspendDialog
        open={suspendOpen}
        title={sd("suspendTitle")}
        description={sd("suspendDesc")}
        confirmLabel={sd("suspendConfirm")}
        onCancel={() => setSuspendOpen(false)}
        onConfirm={(r) => void onSuspend(r)}
      />
    </div>
  );
}
