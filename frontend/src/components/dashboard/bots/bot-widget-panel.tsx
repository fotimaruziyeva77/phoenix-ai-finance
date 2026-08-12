"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useBotWidget } from "@/hooks/useBotWidget";
import type { BotWidgetConfigDto } from "@/lib/api/bot-widget";
import {
  buildWidgetEmbedSnippet,
  getDashboardApiBaseUrl,
  getWidgetScriptSrcForSnippet,
} from "@/lib/widget/build-embed-snippet";

import baseStyles from "./bot-detail.module.css";
import styles from "./bot-widget-panel.module.css";

type Props = {
  botId: string;
};

type Draft = {
  enabled: boolean;
  domainsText: string;
  welcomeText: string;
  theme: string;
};

function domainsFromText(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function draftFromConfig(config: BotWidgetConfigDto): Draft {
  return {
    enabled: config.is_enabled,
    domainsText: config.allowed_domains.join("\n"),
    welcomeText: config.welcome_text ?? "",
    theme: config.theme ?? "",
  };
}

export function BotWidgetPanel({ botId }: Props) {
  const { t } = useLanguage();
  const { loadStatus, config, loadError, saveError, saveSuccess, isSaving, refresh, save } = useBotWidget(
    botId,
    true,
  );

  const [draft, setDraft] = useState<Draft | null>(null);
  const [copyHint, setCopyHint] = useState<"idle" | "copied" | "error">("idle");

  useEffect(() => {
    if (!config) return;
    setDraft(draftFromConfig(config));
  }, [config]);

  const snippet = useMemo(() => {
    if (!config) return "";
    return buildWidgetEmbedSnippet({
      publicWidgetKey: config.public_widget_key,
      apiBaseUrl: getDashboardApiBaseUrl(),
      scriptSrc: getWidgetScriptSrcForSnippet(),
    });
  }, [config]);

  const apiBaseConfigured = getDashboardApiBaseUrl().length > 0;
  const scriptEnv = (process.env.NEXT_PUBLIC_WIDGET_SCRIPT_URL ?? "").trim();
  const scriptConfigured = scriptEnv.length > 0;

  const onSave = useCallback(async () => {
    if (!draft) return;
    await save({
      is_enabled: draft.enabled,
      allowed_domains_json: domainsFromText(draft.domainsText),
      theme: draft.theme.trim() === "" ? null : draft.theme.trim(),
      welcome_text: draft.welcomeText.trim() === "" ? null : draft.welcomeText.trim(),
    });
  }, [draft, save]);

  const onCopySnippet = useCallback(async () => {
    if (!snippet) return;
    try {
      await navigator.clipboard.writeText(snippet);
      setCopyHint("copied");
      window.setTimeout(() => setCopyHint("idle"), 2200);
    } catch {
      setCopyHint("error");
    }
  }, [snippet]);

  if (loadStatus === "loading" || loadStatus === "idle") {
    return <p className={baseStyles.rowMeta}>{t("dashboard.botWidget.loading") as string}</p>;
  }

  if (loadStatus === "error") {
    return (
      <div className={baseStyles.stack}>
        <p className={styles.errorBanner} role="alert" data-testid="bot-widget-load-error">
          {loadError ?? (t("dashboard.botWidget.loadError") as string)}
        </p>
        <button type="button" className={styles.secondaryBtn} onClick={() => void refresh()}>
          {t("dashboard.botWidget.retry") as string}
        </button>
      </div>
    );
  }

  if (!config || !draft) {
    return null;
  }

  return (
    <div className={baseStyles.stack} data-testid="bot-widget-panel">
      <p className={styles.lead}>{t("dashboard.botWidget.lead") as string}</p>

      <div className={styles.split}>
        <section className={baseStyles.card} aria-label="Widget configuration">
          <h3 className={styles.panelTitle}>{t("dashboard.botWidget.settingsTitle") as string}</h3>
          <p className={styles.panelHint}>
            {t("dashboard.botWidget.settingsHint") as string}
          </p>

          <div className={styles.switchRow}>
            <div className={styles.switchLabel}>
              <span className={styles.switchTitle} id="widget-enabled-label">
                {t("dashboard.botWidget.enabledTitle") as string}
              </span>
              <span className={styles.switchMeta}>{t("dashboard.botWidget.enabledMeta") as string}</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={draft.enabled}
              aria-labelledby="widget-enabled-label"
              className={`${styles.switchBtn} ${draft.enabled ? styles.switchBtnOn : styles.switchBtnOff}`}
              onClick={() => setDraft((d) => (d ? { ...d, enabled: !d.enabled } : d))}
              data-testid="bot-widget-enabled-switch"
            >
              <span className={`${styles.switchKnob} ${draft.enabled ? styles.switchKnobOn : ""}`} />
            </button>
          </div>

          <div className={`${baseStyles.field} ${baseStyles.stack}`} style={{ marginTop: "0.85rem" }}>
            <label className={baseStyles.label} htmlFor="widget-domains">
              {t("dashboard.botWidget.allowedDomains") as string}
            </label>
            <textarea
              id="widget-domains"
              className={baseStyles.textarea}
              style={{ minHeight: "5.5rem" }}
              value={draft.domainsText}
              onChange={(e) => setDraft((d) => (d ? { ...d, domainsText: e.target.value } : d))}
              placeholder={"example.com\nwww.example.com"}
              spellCheck={false}
              data-testid="bot-widget-domains"
            />
            <p className={baseStyles.fieldHint}>{t("dashboard.botWidget.domainsHint") as string}</p>
          </div>

          <div className={baseStyles.field} style={{ marginTop: "0.65rem" }}>
            <label className={baseStyles.label} htmlFor="widget-welcome">
              {t("dashboard.botWidget.welcomeLabel") as string}
            </label>
            <textarea
              id="widget-welcome"
              className={baseStyles.textarea}
              style={{ minHeight: "4.5rem" }}
              value={draft.welcomeText}
              onChange={(e) => setDraft((d) => (d ? { ...d, welcomeText: e.target.value } : d))}
              placeholder={t("dashboard.botWidget.welcomePlaceholder") as string}
              data-testid="bot-widget-welcome"
            />
          </div>

          <div className={baseStyles.field} style={{ marginTop: "0.65rem" }}>
            <label className={baseStyles.label} htmlFor="widget-theme">
              {t("dashboard.botWidget.themeLabel") as string}
            </label>
            <select
              id="widget-theme"
              className={baseStyles.select}
              value={draft.theme}
              onChange={(e) => setDraft((d) => (d ? { ...d, theme: e.target.value } : d))}
              data-testid="bot-widget-theme"
            >
              <option value="">{t("dashboard.botWidget.themeAuto") as string}</option>
              <option value="light">{t("dashboard.botWidget.themeLight") as string}</option>
              <option value="dark">{t("dashboard.botWidget.themeDark") as string}</option>
            </select>
            <p className={baseStyles.fieldHint}>{t("dashboard.botWidget.themeHint") as string}</p>
          </div>

          {saveError ? (
            <p className={styles.errorBanner} role="alert" data-testid="bot-widget-save-error">
              {saveError}
            </p>
          ) : null}
          {saveSuccess ? (
            <p className={styles.successBanner} role="status" aria-live="polite" data-testid="bot-widget-save-success">
              {saveSuccess}
            </p>
          ) : null}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.saveBtn}
              disabled={isSaving}
              onClick={() => void onSave()}
              data-testid="bot-widget-save-btn"
            >
              {isSaving
                ? (t("dashboard.botWidget.saving") as string)
                : (t("dashboard.botWidget.saveBtn") as string)}
            </button>
          </div>
        </section>

        <section className={baseStyles.card} aria-label="Install widget">
          <h3 className={styles.panelTitle}>{t("dashboard.botWidget.installTitle") as string}</h3>
          <p className={styles.panelHint}>
            {t("dashboard.botWidget.installHint") as string}
          </p>

          <div className={styles.keyRow}>
            <span className={baseStyles.label}>{t("dashboard.botWidget.publicKeyLabel") as string}</span>
            <code className={styles.keyValue} data-testid="bot-widget-public-key">
              {config.public_widget_key}
            </code>
          </div>

          <ul className={styles.checklist}>
            <li>{t("dashboard.botWidget.checklistBuild") as string} ({`embed/widget`} → {`dist/botforge-widget.js`}).</li>
            <li>
              {t("dashboard.botWidget.checklistHost") as string}
              {!scriptConfigured ? (
                <>
                  {t("dashboard.botWidget.checklistHostSetPre") as string}
                  {`NEXT_PUBLIC_WIDGET_SCRIPT_URL`}
                  {t("dashboard.botWidget.checklistHostSetPost") as string}
                </>
              ) : (
                <>{t("dashboard.botWidget.checklistHostConfigured") as string}</>
              )}
            </li>
            {!apiBaseConfigured ? (
              <li>
                {t("dashboard.botWidget.checklistApiPre") as string}
                {`NEXT_PUBLIC_API_BASE_URL`}
                {t("dashboard.botWidget.checklistApiMid") as string}
                <code>YOUR_API_BASE_URL</code>
                {t("dashboard.botWidget.checklistApiPost") as string}
              </li>
            ) : null}
          </ul>

          <div className={styles.snippetCard}>
            <div className={styles.snippetToolbar}>
              <p className={styles.snippetToolbarTitle}>{t("dashboard.botWidget.embedSnippet") as string}</p>
              <button
                type="button"
                className={styles.copyBtn}
                onClick={() => void onCopySnippet()}
                disabled={!snippet}
                data-testid="bot-widget-copy-snippet"
              >
                {t("dashboard.botWidget.copySnippet") as string}
              </button>
            </div>
            <pre className={styles.snippetPre} data-testid="bot-widget-snippet">
              {snippet}
            </pre>
          </div>
          <p
            className={`${styles.copyMeta} ${copyHint === "copied" ? styles.copyMetaOk : ""} ${copyHint === "error" ? styles.copyMetaErr : ""}`}
            role="status"
            aria-live="polite"
            data-testid="bot-widget-copy-status"
          >
            {copyHint === "copied" ? (t("dashboard.botWidget.copied") as string) : null}
            {copyHint === "error" ? (t("dashboard.botWidget.copyError") as string) : null}
            {copyHint === "idle" ? "\u00a0" : null}
          </p>
        </section>
      </div>
    </div>
  );
}
