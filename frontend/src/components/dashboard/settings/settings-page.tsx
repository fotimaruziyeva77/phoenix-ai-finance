"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import { useTelegramLinking } from "@/hooks/useTelegramLinking";
import { apiFetchWithAuth } from "@/lib/api/client";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { updateProfile, changePassword } from "@/lib/api/auth";
import { formatLocalizedDate, formatLocalizedDateTime } from "@/lib/format/datetime";

import styles from "./settings-page.module.css";

// ─── 2FA types ───────────────────────────────────────────────────────────────

type TotpStatus = { is_configured: boolean; is_active: boolean };
type TotpSetup = { secret: string; provisioning_uri: string; recovery_codes: string[] };

// ─── types ────────────────────────────────────────────────────────────────────

type SessionItem = {
  id: string;
  created_at: string;
  last_used_at: string | null;
  user_agent: string | null;
  ip_address: string | null;
};

type SessionsResponse = {
  items: SessionItem[];
};

type TFn = ReturnType<typeof useLanguage>["t"];

// ─── helpers ──────────────────────────────────────────────────────────────────

function initials(name: string | null | undefined, email: string): string {
  if (name?.trim()) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
    return name.trim().slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

// ─── main component ───────────────────────────────────────────────────────────

export function SettingsPage() {
  const { t, lang } = useLanguage();
  const { user, accessToken, logout, refreshProfile } = useAuth();

  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  const [resendLoading, setResendLoading] = useState(false);
  const [resendMsg, setResendMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const [logoutAllLoading, setLogoutAllLoading] = useState(false);
  const [logoutAllMsg, setLogoutAllMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Account deletion
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Data export
  const [exportLoading, setExportLoading] = useState(false);
  const [exportMsg, setExportMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // 2FA
  const [totpStatus, setTotpStatus] = useState<TotpStatus | null>(null);
  const [totpSetup, setTotpSetup] = useState<TotpSetup | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [totpBusy, setTotpBusy] = useState(false);
  const [totpMsg, setTotpMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Change password
  const [pwFormOpen, setPwFormOpen] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwMsg, setPwMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  // Profile edit
  const [editName, setEditName] = useState<string>("");
  const [nameEditing, setNameEditing] = useState(false);
  const [nameSaving, setNameSaving] = useState(false);
  const [nameMsg, setNameMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);


  // load active sessions
  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const data = await apiFetchWithAuth<SessionsResponse>(
          "/api/v1/auth/sessions",
          accessToken,
          { method: "GET" },
        );
        if (alive) setSessions(data.items);
      } catch {
        // silently ignore — sessions panel becomes empty
      } finally {
        if (alive) setSessionsLoading(false);
      }
    }
    load();
    return () => { alive = false; };
  }, [accessToken]);

  // Load 2FA status
  useEffect(() => {
    let alive = true;
    apiFetchWithAuth<TotpStatus>("/api/v1/auth/2fa/status", accessToken, { method: "GET" })
      .then((data) => { if (alive) setTotpStatus(data); })
      .catch(() => { /* ignore */ });
    return () => { alive = false; };
  }, [accessToken]);

  const handleSetup2FA = useCallback(async () => {
    setTotpBusy(true);
    setTotpMsg(null);
    try {
      const data = await apiFetchWithAuth<TotpSetup>("/api/v1/auth/2fa/setup", accessToken, { method: "POST" });
      setTotpSetup(data);
    } catch (e: unknown) {
      setTotpMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setTotpBusy(false);
    }
  }, [accessToken]);

  const handleActivate2FA = useCallback(async () => {
    if (!totpCode.trim()) return;
    setTotpBusy(true);
    setTotpMsg(null);
    try {
      await apiFetchWithAuth("/api/v1/auth/2fa/activate", accessToken, {
        method: "POST",
        body: { code: totpCode.trim() },
      });
      setTotpStatus({ is_configured: true, is_active: true });
      setTotpSetup(null);
      setTotpCode("");
      setTotpMsg({ type: "ok", text: t("dashboard.settings.twoFactorActivated") as string });
    } catch (e: unknown) {
      setTotpMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setTotpBusy(false);
    }
  }, [accessToken, totpCode, t]);

  const handleDisable2FA = useCallback(async () => {
    if (!confirm(t("dashboard.settings.twoFactorDisableConfirm") as string)) return;
    setTotpBusy(true);
    setTotpMsg(null);
    try {
      await apiFetchWithAuth("/api/v1/auth/2fa", accessToken, { method: "DELETE" });
      setTotpStatus({ is_configured: false, is_active: false });
      setTotpSetup(null);
      setTotpMsg({ type: "ok", text: t("dashboard.settings.twoFactorDisabled") as string });
    } catch (e: unknown) {
      setTotpMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setTotpBusy(false);
    }
  }, [accessToken, t]);

  const handleResendVerification = useCallback(async () => {
    setResendLoading(true);
    setResendMsg(null);
    try {
      await apiFetchWithAuth("/api/v1/auth/resend-verification", accessToken, {
        method: "POST",
      });
      setResendMsg({ type: "ok", text: t("dashboard.settings.verificationSent") as string });
    } catch (e: unknown) {
      setResendMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setResendLoading(false);
    }
  }, [accessToken, t]);

  const handleChangePassword = useCallback(async () => {
    setPwMsg(null);

    // Client-side validation
    if (newPw.length < 8) {
      setPwMsg({ type: "err", text: t("dashboard.settings.passwordTooShort") as string });
      return;
    }
    if (newPw !== confirmPw) {
      setPwMsg({ type: "err", text: t("dashboard.settings.passwordsDoNotMatch") as string });
      return;
    }

    setPwLoading(true);
    try {
      await changePassword(accessToken, currentPw, newPw);
      setPwMsg({ type: "ok", text: t("dashboard.settings.passwordChanged") as string });
      setPwFormOpen(false);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (e: unknown) {
      const msg = parseApiErrorMessage(e);
      if (msg.includes("invalid_current_password") || msg.includes("Current password")) {
        setPwMsg({ type: "err", text: t("dashboard.settings.wrongCurrentPassword") as string });
      } else {
        setPwMsg({ type: "err", text: msg });
      }
    } finally {
      setPwLoading(false);
    }
  }, [accessToken, currentPw, newPw, confirmPw, t]);

  const handleStartEditName = useCallback(() => {
    setEditName(user?.full_name ?? "");
    setNameMsg(null);
    setNameEditing(true);
  }, [user]);

  const handleSaveName = useCallback(async () => {
    setNameSaving(true);
    setNameMsg(null);
    try {
      await updateProfile(accessToken, { full_name: editName.trim() || null });
      await refreshProfile();
      setNameEditing(false);
      setNameMsg({ type: "ok", text: t("dashboard.settings.nameUpdated") as string });
    } catch (e: unknown) {
      setNameMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setNameSaving(false);
    }
  }, [accessToken, editName, refreshProfile, t]);

  const handleLogoutAll = useCallback(async () => {
    if (!confirm(t("dashboard.settings.logoutAllConfirm") as string)) return;
    setLogoutAllLoading(true);
    setLogoutAllMsg(null);
    try {
      await apiFetchWithAuth("/api/v1/auth/logout-all", accessToken, { method: "POST" });
      logout();
    } catch (e: unknown) {
      setLogoutAllMsg({ type: "err", text: parseApiErrorMessage(e) });
      setLogoutAllLoading(false);
    }
  }, [accessToken, logout, t]);

  const handleExportData = useCallback(async () => {
    setExportLoading(true);
    setExportMsg(null);
    try {
      const data = await apiFetchWithAuth<Record<string, unknown>>("/api/v1/auth/me/export", accessToken, {
        method: "GET",
      });
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `botforge-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExportMsg({ type: "ok", text: t("dashboard.settings.exportSuccess") as string });
    } catch (e: unknown) {
      setExportMsg({ type: "err", text: parseApiErrorMessage(e) });
    } finally {
      setExportLoading(false);
    }
  }, [accessToken, t]);

  const handleDeleteAccount = useCallback(async () => {
    setDeleteLoading(true);
    setDeleteMsg(null);
    try {
      await apiFetchWithAuth("/api/v1/auth/me", accessToken, {
        method: "DELETE",
        body: JSON.stringify({ confirm: true }),
        headers: { "Content-Type": "application/json" },
      });
      logout();
    } catch (e: unknown) {
      setDeleteMsg({ type: "err", text: parseApiErrorMessage(e) });
      setDeleteLoading(false);
    }
  }, [accessToken, logout]);

  if (!user) {
    return (
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>{t("dashboard.settings.loading") as string}</p>
      </div>
    );
  }

  const isVerified = !!user.is_verified;
  const hasPassword = user.has_password !== false; // true for password-based, false for OAuth-only
  const displayName = user.full_name?.trim() || user.email;
  const avatarLetters = initials(user.full_name, user.email);

  return (
    <div className={styles.stack}>
      {/* ── Page header ───────────────────────────────────── */}
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>{t("dashboard.settings.title") as string}</h1>
        <p className={styles.pageSubtitle}>{t("dashboard.settings.subtitle") as string}</p>
      </header>

      {/* ── Profile ─────────────────────────────────────── */}
      <div className={styles.card}>
        <p className={styles.cardTitle}>{t("dashboard.settings.profile") as string}</p>
        <div className={styles.profileRow}>
          <div className={styles.avatar}>{avatarLetters}</div>
          <div className={styles.profileInfo}>
            <p className={styles.profileName}>{displayName}</p>
            <p className={styles.profileEmail}>{user.email}</p>
          </div>
        </div>

        <div className={styles.badgeRow}>
          <span className={`${styles.badge} ${styles.badgeRole}`}>{user.role}</span>
          {isVerified ? (
            <span className={`${styles.badge} ${styles.badgeVerified}`}>
              {t("dashboard.settings.emailVerified") as string}
            </span>
          ) : (
            <span className={`${styles.badge} ${styles.badgeUnverified}`}>
              {t("dashboard.settings.emailUnverified") as string}
            </span>
          )}
          <span className={`${styles.badge} ${user.is_active ? styles.badgeActive : styles.badgeInactive}`}>
            {user.is_active
              ? (t("dashboard.settings.active") as string)
              : (t("dashboard.settings.inactive") as string)}
          </span>
        </div>

        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>{t("dashboard.settings.userId") as string}</span>
            <span className={styles.infoValueMono}>{user.id}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>{t("dashboard.settings.memberSince") as string}</span>
            <span className={styles.infoValue}>{formatLocalizedDate(user.created_at, lang)}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>{t("dashboard.settings.lastUpdated") as string}</span>
            <span className={styles.infoValue}>{formatLocalizedDate(user.updated_at, lang)}</span>
          </div>
        </div>

        {/* Edit display name */}
        {nameMsg && (
          <div className={nameMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
            {nameMsg.text}
          </div>
        )}
        {nameEditing ? (
          <div className={styles.editRow}>
            <input
              type="text"
              className={styles.editInput}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder={t("dashboard.settings.displayNamePlaceholder") as string}
              maxLength={256}
              disabled={nameSaving}
            />
            <button className={styles.btnPrimary} onClick={handleSaveName} disabled={nameSaving}>
              {nameSaving
                ? (t("dashboard.settings.saving") as string)
                : (t("dashboard.settings.save") as string)}
            </button>
            <button
              className={styles.btnSecondary}
              onClick={() => { setNameEditing(false); setNameMsg(null); }}
              disabled={nameSaving}
            >
              {t("dashboard.settings.cancel") as string}
            </button>
          </div>
        ) : (
          <div className={styles.btnRow}>
            <button className={styles.btnSecondary} onClick={handleStartEditName}>
              {t("dashboard.settings.editDisplayName") as string}
            </button>
          </div>
        )}
      </div>

      {/* ── Account security ─────────────────────────────── */}
      {hasPassword && (
        <div className={styles.card}>
          <p className={styles.cardTitle}>{t("dashboard.settings.accountSecurity") as string}</p>

          <div>
            <p className={styles.sectionDesc}>
              {isVerified
                ? (t("dashboard.settings.emailVerifiedMsg") as string)
                : (t("dashboard.settings.emailUnverifiedMsg") as string)}
            </p>
            {resendMsg && (
              <div className={resendMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
                {resendMsg.text}
              </div>
            )}
            {!isVerified && (
              <div className={styles.btnRow}>
                <button
                  className={styles.btnPrimary}
                  onClick={handleResendVerification}
                  disabled={resendLoading}
                >
                  {resendLoading
                    ? (t("dashboard.settings.sending") as string)
                    : (t("dashboard.settings.resendVerification") as string)}
                </button>
              </div>
            )}
          </div>

          <div>
            {pwMsg && (
              <div className={pwMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
                {pwMsg.text}
              </div>
            )}
            {pwFormOpen ? (
              <>
                <p className={styles.sectionDesc}>
                  {t("dashboard.settings.changePasswordHint") as string}
                </p>
                <div className={styles.editRow}>
                  <input
                    type="password"
                    className={styles.editInput}
                    value={currentPw}
                    onChange={(e) => setCurrentPw(e.target.value)}
                    placeholder={t("dashboard.settings.currentPassword") as string}
                    disabled={pwLoading}
                    autoComplete="current-password"
                  />
                </div>
                <div className={styles.editRow}>
                  <input
                    type="password"
                    className={styles.editInput}
                    value={newPw}
                    onChange={(e) => setNewPw(e.target.value)}
                    placeholder={t("dashboard.settings.newPassword") as string}
                    disabled={pwLoading}
                    autoComplete="new-password"
                  />
                </div>
                <div className={styles.editRow}>
                  <input
                    type="password"
                    className={styles.editInput}
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    placeholder={t("dashboard.settings.confirmNewPassword") as string}
                    disabled={pwLoading}
                    autoComplete="new-password"
                  />
                </div>
                <div className={styles.btnRow}>
                  <button
                    className={styles.btnPrimary}
                    onClick={handleChangePassword}
                    disabled={pwLoading || !currentPw || !newPw || !confirmPw}
                  >
                    {pwLoading
                      ? (t("dashboard.settings.changingPassword") as string)
                      : (t("dashboard.settings.changePassword") as string)}
                  </button>
                  <button
                    className={styles.btnSecondary}
                    onClick={() => { setPwFormOpen(false); setCurrentPw(""); setNewPw(""); setConfirmPw(""); setPwMsg(null); }}
                    disabled={pwLoading}
                  >
                    {t("dashboard.settings.cancel") as string}
                  </button>
                </div>
              </>
            ) : (
              <div className={styles.btnRow}>
                <button className={styles.btnSecondary} onClick={() => { setPwFormOpen(true); setPwMsg(null); }}>
                  {t("dashboard.settings.changePassword") as string}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Two-Factor Authentication ─────────────────────── */}
      <TwoFactorSection
        t={t}
        totpStatus={totpStatus}
        totpSetup={totpSetup}
        totpCode={totpCode}
        setTotpCode={setTotpCode}
        totpBusy={totpBusy}
        totpMsg={totpMsg}
        setTotpSetup={setTotpSetup}
        setTotpMsg={setTotpMsg}
        onSetup={handleSetup2FA}
        onActivate={handleActivate2FA}
        onDisable={handleDisable2FA}
      />

      {/* ── Active sessions ──────────────────────────────── */}
      <div className={styles.card}>
        <p className={styles.cardTitle}>{t("dashboard.settings.activeSessions") as string}</p>

        {sessionsLoading ? (
          <p className={styles.sectionDesc}>{t("dashboard.settings.loadingSessions") as string}</p>
        ) : sessions.length === 0 ? (
          <p className={styles.sectionDesc}>{t("dashboard.settings.noSessions") as string}</p>
        ) : (
          <div className={styles.sessionList}>
            {sessions.map((s) => (
              <div key={s.id} className={styles.sessionItem}>
                <div className={styles.sessionMeta}>
                  <span className={styles.sessionId}>{s.id.slice(0, 8)}…</span>
                  <span className={styles.sessionCreated}>
                    {t("dashboard.settings.started") as string} {formatLocalizedDateTime(s.created_at, lang)}
                    {s.last_used_at && (
                      <>{" · "}{t("dashboard.settings.lastUsed") as string} {formatLocalizedDateTime(s.last_used_at, lang)}</>
                    )}
                  </span>
                  {(s.user_agent || s.ip_address) && (
                    <span className={styles.sessionCreated}>
                      {[s.ip_address, s.user_agent].filter(Boolean).join(" · ")}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Telegram linking ─────────────────────────────── */}
      <TelegramLinkingSection t={t} lang={lang} />

      {/* ── Quick links ──────────────────────────────────── */}
      <div className={styles.card}>
        <p className={styles.cardTitle}>{t("dashboard.settings.workspace") as string}</p>
        <div className={styles.btnRow}>
          <Link href="/dashboard/billing" className={styles.btnSecondary}>
            {t("dashboard.settings.billingPlans") as string}
          </Link>
          <Link href="/dashboard/bots" className={styles.btnSecondary}>
            {t("dashboard.settings.manageBots") as string}
          </Link>
        </div>
      </div>

      {/* ── Data & Privacy ─────────────────────────────── */}
      <div className={styles.card}>
        <p className={styles.cardTitle}>{t("dashboard.settings.dataPrivacy") as string}</p>
        <p className={styles.sectionDesc}>
          {t("dashboard.settings.exportDesc") as string}
        </p>
        {exportMsg && (
          <div className={exportMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
            {exportMsg.text}
          </div>
        )}
        <div className={styles.btnRow}>
          <button
            className={styles.btnSecondary}
            onClick={handleExportData}
            disabled={exportLoading}
          >
            {exportLoading
              ? (t("dashboard.settings.exporting") as string)
              : (t("dashboard.settings.exportData") as string)}
          </button>
        </div>
      </div>

      {/* ── Danger zone ──────────────────────────────────── */}
      <div className={styles.dangerCard}>
        <p className={styles.dangerTitle}>{t("dashboard.settings.dangerZone") as string}</p>
        <p className={styles.dangerBody}>
          {t("dashboard.settings.logoutAllDesc") as string}
        </p>
        {logoutAllMsg && (
          <div className={logoutAllMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
            {logoutAllMsg.text}
          </div>
        )}
        <div className={styles.btnRow}>
          <button
            className={styles.btnDanger}
            onClick={handleLogoutAll}
            disabled={logoutAllLoading}
          >
            {logoutAllLoading
              ? (t("dashboard.settings.signingOut") as string)
              : (t("dashboard.settings.signOutAll") as string)}
          </button>
        </div>

        <hr className={styles.dangerDivider} />

        <p className={styles.dangerBody}>
          {t("dashboard.settings.deleteAccountDesc") as string}
          {" "}
          <strong>{t("dashboard.settings.cannotBeUndone") as string}</strong>.
        </p>
        {deleteMsg && (
          <div className={deleteMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
            {deleteMsg.text}
          </div>
        )}
        {deleteConfirmOpen ? (
          <div className={styles.confirmRow}>
            <span className={styles.confirmLabel}>
              {t("dashboard.settings.absolutelySure") as string}
            </span>
            <button
              className={styles.btnDanger}
              onClick={handleDeleteAccount}
              disabled={deleteLoading}
            >
              {deleteLoading
                ? (t("dashboard.settings.deleting") as string)
                : (t("dashboard.settings.yesDelete") as string)}
            </button>
            <button
              className={styles.btnSecondary}
              onClick={() => setDeleteConfirmOpen(false)}
              disabled={deleteLoading}
            >
              {t("dashboard.settings.cancel") as string}
            </button>
          </div>
        ) : (
          <div className={styles.btnRow}>
            <button
              className={styles.btnDanger}
              onClick={() => setDeleteConfirmOpen(true)}
            >
              {t("dashboard.settings.deleteAccount") as string}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── 2FA sub-component ────────────────────────────────────────────────────────

function TwoFactorSection({
  t, totpStatus, totpSetup, totpCode, setTotpCode, totpBusy, totpMsg,
  setTotpSetup, setTotpMsg, onSetup, onActivate, onDisable,
}: {
  t: TFn;
  totpStatus: TotpStatus | null;
  totpSetup: TotpSetup | null;
  totpCode: string;
  setTotpCode: (v: string) => void;
  totpBusy: boolean;
  totpMsg: { type: "ok" | "err"; text: string } | null;
  setTotpSetup: (v: TotpSetup | null) => void;
  setTotpMsg: (v: { type: "ok" | "err"; text: string } | null) => void;
  onSetup: () => void;
  onActivate: () => void;
  onDisable: () => void;
}) {
  return (
    <div className={styles.card}>
      <p className={styles.cardTitle}>{t("dashboard.settings.twoFactor") as string}</p>

      {totpMsg && (
        <div className={totpMsg.type === "ok" ? styles.alertSuccess : styles.alertError}>
          {totpMsg.text}
        </div>
      )}

      {totpStatus?.is_active ? (
        <div>
          <p className={styles.sectionDesc}>
            {t("dashboard.settings.twoFactor") as string}{" "}
            <strong>{t("dashboard.settings.active") as string}</strong>.{" "}
            {t("dashboard.settings.twoFactorProtected") as string}
          </p>
          <div className={styles.btnRow}>
            <button className={styles.btnDanger} onClick={onDisable} disabled={totpBusy}>
              {totpBusy
                ? (t("dashboard.settings.disabling") as string)
                : (t("dashboard.settings.disable2fa") as string)}
            </button>
          </div>
        </div>
      ) : totpSetup ? (
        <div>
          <p className={styles.sectionDesc}>
            {t("dashboard.settings.scanQrCode") as string}
          </p>
          <div className={styles.qrWrap}>
            <img
              className={styles.qrImage}
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpSetup.provisioning_uri)}`}
              alt="TOTP QR Code"
              width={200}
              height={200}
            />
          </div>
          <p className={styles.codeLabel}>{t("dashboard.settings.manualEntryKey") as string}</p>
          <code className={styles.codeBlock}>{totpSetup.secret}</code>

          <p className={styles.codeLabel}>{t("dashboard.settings.recoveryCodes") as string}</p>
          <div className={styles.recoveryGrid}>
            {totpSetup.recovery_codes.map((c) => (
              <span key={c}>{c}</span>
            ))}
          </div>

          <div className={styles.editRow}>
            <input
              type="text"
              className={styles.totpInput}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              placeholder={t("dashboard.settings.totpPlaceholder") as string}
              maxLength={8}
              disabled={totpBusy}
            />
            <button className={styles.btnPrimary} onClick={onActivate} disabled={totpBusy || !totpCode.trim()}>
              {totpBusy
                ? (t("dashboard.settings.verifying") as string)
                : (t("dashboard.settings.activate") as string)}
            </button>
            <button
              className={styles.btnSecondary}
              onClick={() => { setTotpSetup(null); setTotpCode(""); setTotpMsg(null); }}
              disabled={totpBusy}
            >
              {t("dashboard.settings.cancel") as string}
            </button>
          </div>
        </div>
      ) : (
        <div>
          <p className={styles.sectionDesc}>
            {t("dashboard.settings.twoFactorDesc") as string}
          </p>
          <div className={styles.btnRow}>
            <button className={styles.btnPrimary} onClick={onSetup} disabled={totpBusy}>
              {totpBusy
                ? (t("dashboard.settings.settingUp") as string)
                : (t("dashboard.settings.setUp2fa") as string)}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Telegram Linking sub-component ──────────────────────────────────────────

function TelegramLinkingSection({
  t,
  lang,
}: {
  t: TFn;
  lang: string;
}) {
  const { status, loading, unlinking, errorMessage, unlink } = useTelegramLinking();

  if (loading) {
    return (
      <div className={styles.card}>
        <p className={styles.cardTitle}>{t("dashboard.settings.telegramTitle") as string}</p>
        <p className={styles.sectionDesc}>{t("dashboard.settings.loading") as string}</p>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <p className={styles.cardTitle}>{t("dashboard.settings.telegramTitle") as string}</p>

      {errorMessage && (
        <div className={styles.alertError}>{errorMessage}</div>
      )}

      {status?.isLinked ? (
        <>
          <p className={styles.sectionDesc}>
            {t("dashboard.settings.telegramLinkedMsg") as string}
          </p>
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <span className={styles.infoLabel}>Chat ID</span>
              <span className={styles.infoValueMono}>{status.telegramChatId}</span>
            </div>
            {status.linkedAt && (
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>
                  {t("dashboard.settings.telegramLinkedAt") as string}
                </span>
                <span className={styles.infoValue}>
                  {formatLocalizedDateTime(status.linkedAt, lang)}
                </span>
              </div>
            )}
          </div>
          <div className={styles.badgeRow}>
            <span className={`${styles.badge} ${styles.badgeVerified}`}>
              {t("dashboard.settings.telegramConnected") as string}
            </span>
          </div>
          <div className={styles.btnRow}>
            <button
              className={styles.btnDanger}
              onClick={unlink}
              disabled={unlinking}
            >
              {unlinking
                ? (t("dashboard.settings.telegramUnlinking") as string)
                : (t("dashboard.settings.telegramUnlink") as string)}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className={styles.sectionDesc}>
            {t("dashboard.settings.telegramDesc") as string}
          </p>
          {status?.linkUrl ? (
            <div className={styles.btnRow}>
              <a
                href={status.linkUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.btnPrimary}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  style={{ width: "1rem", height: "1rem", marginRight: "0.45rem" }}
                  aria-hidden
                >
                  <path
                    d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7Z"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {t("dashboard.settings.telegramLink") as string}
              </a>
            </div>
          ) : (
            <p className={styles.sectionDesc}>
              {t("dashboard.settings.telegramNotConfigured") as string}
            </p>
          )}
        </>
      )}
    </div>
  );
}
