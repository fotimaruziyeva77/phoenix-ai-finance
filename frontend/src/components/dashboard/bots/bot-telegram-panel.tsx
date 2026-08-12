"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import { useBotTelegram } from "@/hooks/useBotTelegram";
import { fetchSubscription, type SubscriptionDto } from "@/lib/api/billing";
import type { BotTelegramStatusDto } from "@/lib/api/bot-telegram";
import { formatLocalizedDateTime } from "@/lib/format/datetime";

import baseStyles from "./bot-detail.module.css";
import styles from "./bot-telegram-panel.module.css";

type Props = {
  botId: string;
  archived?: boolean;
};

function telegramStatusPill(status: BotTelegramStatusDto): { key: string; ok: boolean } {
  if (status.channel_status === "active") return { key: "pillActive", ok: true };
  if (status.channel_status === "failed_validation") return { key: "pillValidationFailed", ok: false };
  if (status.channel_status === "channel_pending") return { key: "pillSetupInProgress", ok: false };
  return { key: "pillNotStarted", ok: false };
}

function formatVerifiedAt(iso: string | null, lang: string): string | null {
  if (!iso) return null;
  const out = formatLocalizedDateTime(iso, lang);
  return out === "—" ? null : out;
}

const FREE_PLAN_SLUGS = new Set(["free"]);

export function BotTelegramPanel({ botId, archived = false }: Props) {
  const { t, lang } = useLanguage();
  const { accessToken } = useAuth();
  const {
    loadStatus,
    status,
    loadError,
    actionError,
    successMessage,
    isConnecting,
    isDisconnecting,
    refresh,
    connect,
    disconnect,
  } = useBotTelegram(botId, true);

  const [tokenDraft, setTokenDraft] = useState("");
  const [planSlug, setPlanSlug] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchSubscription(accessToken)
      .then((sub: SubscriptionDto) => {
        if (alive) setPlanSlug(sub.plan_slug);
      })
      .catch(() => {
        if (alive) setPlanSlug("free");
      });
    return () => { alive = false; };
  }, [accessToken]);

  useEffect(() => {
    if (successMessage) setTokenDraft("");
  }, [successMessage]);

  const onConnect = useCallback(async () => {
    await connect(tokenDraft);
  }, [connect, tokenDraft]);

  if (loadStatus === "loading" || loadStatus === "idle") {
    return <p className={baseStyles.rowMeta}>{t("dashboard.botTelegram.loading") as string}</p>;
  }

  if (loadStatus === "error") {
    return (
      <div className={baseStyles.stack}>
        <p className={styles.errorBanner} role="alert" data-testid="bot-telegram-load-error">
          {loadError ?? (t("dashboard.botTelegram.loadError") as string)}
        </p>
        <button type="button" className={styles.secondaryBtn} onClick={() => void refresh()}>
          {t("dashboard.botTelegram.retry") as string}
        </button>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const pill = telegramStatusPill(status);
  const live = status.channel_status === "active";
  const hasStoredToken = status.configured;
  const busy = isConnecting || isDisconnecting;
  const canDisconnect = status.channel_status !== "draft";
  const isFreePlan = planSlug !== null && FREE_PLAN_SLUGS.has(planSlug);

  // Show upgrade banner if user is on Free plan and Telegram is not yet connected
  if (isFreePlan && !live) {
    return (
      <div className={baseStyles.stack} data-testid="bot-telegram-panel">
        <p className={styles.lead}>{t("dashboard.botTelegram.lead") as string}</p>
        <div className={styles.upgradeBanner} data-testid="bot-telegram-upgrade-banner">
          <strong>{t("dashboard.botTelegram.upgradeTitle") as string}</strong>
          <p style={{ margin: "0.35rem 0 0", fontSize: "0.85rem", opacity: 0.85 }}>
            {t("dashboard.botTelegram.upgradeDesc") as string}
          </p>
          <Link href="/dashboard/billing" className={styles.upgradeBtn}>
            {t("dashboard.botTelegram.upgradeBtn") as string}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={baseStyles.stack} data-testid="bot-telegram-panel">
      <p className={styles.lead}>{t("dashboard.botTelegram.lead") as string}</p>

      <div className={styles.botfatherNote} data-testid="bot-telegram-botfather-note">
        <strong>{t("dashboard.botTelegram.botfatherTitle") as string}</strong>
        {t("dashboard.botTelegram.botfatherIntro") as string}
        <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer">
          @BotFather
        </a>
        {t("dashboard.botTelegram.botfatherRun") as string}
        <code>/newbot</code>
        {t("dashboard.botTelegram.botfatherSelect") as string}
        <strong>{t("dashboard.botTelegram.apiToken") as string}</strong>
        {t("dashboard.botTelegram.botfatherFormat") as string}
        <code>123456789:AA…</code>
        {t("dashboard.botTelegram.botfatherPaste") as string}
        <strong>{t("dashboard.botTelegram.neverShow") as string}</strong>
        {t("dashboard.botTelegram.botfatherEnd") as string}
      </div>

      <section className={baseStyles.card} aria-label="Telegram connection">
        <h3 className={styles.panelTitle}>{t("dashboard.botTelegram.connectionTitle") as string}</h3>

        <div className={styles.statusRow}>
          <span
            className={`${styles.statusPill} ${pill.ok ? styles.statusPillOk : styles.statusPillOff}`}
            data-testid="bot-telegram-status-pill"
          >
            {t("dashboard.botTelegram." + pill.key) as string}
          </span>
          {status.webhook_url_configured ? (
            <span className={styles.usernameMuted} data-testid="bot-telegram-webhook-hint">
              {t("dashboard.botTelegram.webhookRegistered") as string}
            </span>
          ) : null}
        </div>

        <p className={styles.usernameLine} data-testid="bot-telegram-username-line">
          {status.bot_username ? (
            <>
              {t("dashboard.botTelegram.botUsernamePrefix") as string}
              <strong data-testid="bot-telegram-username">@{status.bot_username}</strong>
            </>
          ) : (
            <span className={styles.usernameMuted}>
              {live
                ? (t("dashboard.botTelegram.usernameAfterConfirm") as string)
                : (t("dashboard.botTelegram.usernameConnect") as string)}
            </span>
          )}
        </p>
        {formatVerifiedAt(status.last_verified_at, lang) ? (
          <p className={styles.metaLine} data-testid="bot-telegram-last-verified">
            {t("dashboard.botTelegram.lastVerifiedPrefix") as string}
            {formatVerifiedAt(status.last_verified_at, lang)}
          </p>
        ) : null}

        {archived ? (
          <p className={styles.errorBanner} role="status" data-testid="bot-telegram-archived-notice">
            {t("dashboard.botTelegram.archivedNotice") as string}
          </p>
        ) : null}

        {actionError ? (
          <p className={styles.errorBanner} role="alert" data-testid="bot-telegram-action-error">
            {actionError}
          </p>
        ) : null}
        {successMessage ? (
          <p
            className={styles.successBanner}
            role="status"
            aria-live="polite"
            data-testid="bot-telegram-success"
          >
            {successMessage}
          </p>
        ) : null}

        {status.last_error_code ? (
          <p className={styles.errorBanner} role="status" data-testid="bot-telegram-last-error">
            {t("dashboard.botTelegram.lastIssuePrefix") as string}
            {status.last_error_code.replace(/_/g, " ")}
          </p>
        ) : null}

        <div className={styles.tokenField}>
          <label className={styles.tokenLabel} htmlFor="telegram-bot-token">
            {t("dashboard.botTelegram.botTokenLabel") as string}
          </label>
          <p className={styles.tokenHint}>
            {t("dashboard.botTelegram.botTokenHint") as string}
          </p>
          <input
            id="telegram-bot-token"
            className={styles.tokenInput}
            type="password"
            name="telegram_bot_token"
            autoComplete="off"
            spellCheck={false}
            placeholder={
              hasStoredToken
                ? (t("dashboard.botTelegram.tokenPlaceholderStored") as string)
                : (t("dashboard.botTelegram.tokenPlaceholderEmpty") as string)
            }
            value={tokenDraft}
            onChange={(e) => setTokenDraft(e.target.value)}
            disabled={archived || busy}
            data-testid="bot-telegram-token-input"
          />
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.connectBtn}
            onClick={() => void onConnect()}
            disabled={archived || busy || tokenDraft.trim().length < 10}
            data-testid="bot-telegram-connect"
          >
            {isConnecting
              ? (t("dashboard.botTelegram.connecting") as string)
              : hasStoredToken
                ? (t("dashboard.botTelegram.updateConnection") as string)
                : (t("dashboard.botTelegram.connectTelegram") as string)}
          </button>
          <button
            type="button"
            className={styles.disconnectBtn}
            onClick={() => void disconnect()}
            disabled={!canDisconnect || busy}
            data-testid="bot-telegram-disconnect"
          >
            {isDisconnecting
              ? (t("dashboard.botTelegram.disconnecting") as string)
              : (t("dashboard.botTelegram.disconnect") as string)}
          </button>
        </div>
      </section>
    </div>
  );
}
