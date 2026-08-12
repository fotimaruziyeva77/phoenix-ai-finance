"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { BotKnowledgePanel } from "@/components/dashboard/bots/knowledge/bot-knowledge-panel";
import { BotTestChatPanel } from "@/components/dashboard/bots/bot-test-chat-panel";
import { BotTelegramPanel } from "@/components/dashboard/bots/bot-telegram-panel";
import { BotWidgetPanel } from "@/components/dashboard/bots/bot-widget-panel";
import { BotStatusBadge } from "@/components/dashboard/bots/bot-status-badge";
import { useLanguage } from "@/contexts/language-context";
import { useBotDetail } from "@/hooks/useBotDetail";
import { inferenceProviderLabel } from "@/lib/bot-domain/inference-provider-label";
import { toFriendlyGoalLabel, toFriendlyNicheLabel } from "@/lib/bot-domain/labels";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import styles from "./bot-detail.module.css";

type Props = {
  botId: string;
};

type FormState = {
  name: string;
  welcomeMessage: string;
  tone: string;
  language: string;
  shortDescription: string;
  status: "draft" | "active" | "paused" | "archived";
  modelName: string;
  temperatureText: string;
  maxOutputTokensText: string;
};

function toNullableTrimmed(value: string): string | null {
  const v = value.trim();
  return v.length > 0 ? v : null;
}

function parseOptionalTemperature(raw: string): number | null | "invalid" {
  const t = raw.trim();
  if (!t) return null;
  const n = Number(t);
  if (!Number.isFinite(n) || n < 0 || n > 2) return "invalid";
  return n;
}

function parseOptionalMaxOutputTokens(raw: string): number | null | "invalid" {
  const t = raw.trim();
  if (!t) return null;
  const n = parseInt(t, 10);
  if (!Number.isFinite(n) || String(n) !== t.trim() || n < 1 || n > 8192) return "invalid";
  return n;
}

export function BotDetailPage({ botId }: Props) {
  const { t } = useLanguage();
  const { status, bot, errorMessage, saveError, saveSuccess, isSaving, isArchiving, isDeleting, refresh, save, archive, hardDelete } =
    useBotDetail(botId);

  const initialForm = useMemo<FormState | null>(() => {
    if (!bot) return null;
    return {
      name: bot.name,
      welcomeMessage: bot.welcome_message ?? "",
      tone: bot.tone ?? "",
      language: bot.language ?? "",
      shortDescription: bot.short_description ?? "",
      status: bot.status,
      modelName: bot.model_name ?? "",
      temperatureText:
        bot.temperature !== null && bot.temperature !== undefined ? String(bot.temperature) : "",
      maxOutputTokensText:
        bot.max_output_tokens !== null && bot.max_output_tokens !== undefined
          ? String(bot.max_output_tokens)
          : "",
    };
  }, [bot]);

  const [form, setForm] = useState<FormState | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [isArchiveConfirmOpen, setIsArchiveConfirmOpen] = useState(false);
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"settings" | "knowledge" | "widget" | "telegram">("settings");
  const activeForm = form ?? initialForm;
  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => {
      const base = prev ?? initialForm;
      if (!base) return prev;
      return { ...base, [key]: value };
    });
  };

  if (status === "loading" || status === "idle") {
    return <p className={styles.rowMeta}>{t("dashboard.botDetail.loadingBot") as string}</p>;
  }

  if (status === "error") {
    return (
      <div className={styles.stack}>
        <p className={styles.errorBanner} data-testid="bot-detail-load-error">
          {errorMessage ?? (t("dashboard.botDetail.loadError") as string)}
        </p>
        <div className={styles.actions}>
          <button type="button" className={styles.saveBtn} onClick={() => void refresh()}>
            {t("dashboard.botDetail.retry") as string}
          </button>
          <Link href="/dashboard/bots" className={styles.backLink}>
            {t("dashboard.botDetail.backToBots") as string}
          </Link>
        </div>
      </div>
    );
  }

  if (!bot || !activeForm) {
    return null;
  }

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanName = activeForm.name.trim();
    if (cleanName.length < 2) return;

    const temp = parseOptionalTemperature(activeForm.temperatureText);
    if (temp === "invalid") {
      setClientError(t("dashboard.botDetail.temperatureInvalid") as string);
      return;
    }
    const maxTok = parseOptionalMaxOutputTokens(activeForm.maxOutputTokensText);
    if (maxTok === "invalid") {
      setClientError(t("dashboard.botDetail.maxTokensInvalid") as string);
      return;
    }
    setClientError(null);

    await save({
      name: cleanName,
      welcome_message: toNullableTrimmed(activeForm.welcomeMessage),
      tone: toNullableTrimmed(activeForm.tone),
      language: toNullableTrimmed(activeForm.language),
      short_description: toNullableTrimmed(activeForm.shortDescription),
      status: activeForm.status,
      model_name: toNullableTrimmed(activeForm.modelName),
      temperature: temp,
      max_output_tokens: maxTok,
    });
    setForm(null);
  };

  return (
    <div className={styles.stack} data-testid="bot-detail-page">
      <header className={styles.headerRow}>
        <div>
          <h2 className={styles.title}>{bot.name}</h2>
          <p className={styles.meta}>{t("dashboard.botDetail.subtitle") as string}</p>
        </div>
        <Link href="/dashboard/bots" className={styles.backLink}>
          {t("dashboard.botDetail.backToBots") as string}
        </Link>
      </header>

      <nav className={styles.tabStrip} aria-label="Bot sections" data-testid="bot-detail-tabs">
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === "settings" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("settings")}
          data-testid="bot-detail-tab-settings"
        >
          {t("dashboard.botDetail.tabSettings") as string}
        </button>
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === "knowledge" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("knowledge")}
          data-testid="bot-detail-tab-knowledge"
        >
          {t("dashboard.botDetail.tabKnowledge") as string}
        </button>
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === "widget" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("widget")}
          data-testid="bot-detail-tab-widget"
        >
          {t("dashboard.botDetail.tabWidget") as string}
        </button>
        <button
          type="button"
          className={`${styles.tabBtn} ${activeTab === "telegram" ? styles.tabBtnActive : ""}`}
          onClick={() => setActiveTab("telegram")}
          data-testid="bot-detail-tab-telegram"
        >
          {t("dashboard.botDetail.tabTelegram") as string}
        </button>
      </nav>

      {activeTab === "knowledge" ? (
        <div className={styles.card}>
          <BotKnowledgePanel botId={botId} uploadsDisabled={bot.status === "archived"} />
        </div>
      ) : null}

      {activeTab === "widget" ? <BotWidgetPanel botId={botId} /> : null}

      {activeTab === "telegram" ? (
        <BotTelegramPanel botId={botId} archived={bot.status === "archived"} />
      ) : null}

      {activeTab === "settings" ? (
        <>
      <section className={styles.card} aria-label="Bot metadata">
        <div className={styles.grid}>
          <div className={styles.field}>
            <span className={styles.label}>{t("dashboard.botDetail.niche") as string}</span>
            <p className={styles.readonlyValue}>{toFriendlyNicheLabel(bot.niche_id)}</p>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>{t("dashboard.botDetail.goal") as string}</span>
            <p className={styles.readonlyValue}>{toFriendlyGoalLabel(bot.goal_type)}</p>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>{t("dashboard.botDetail.currentStatus") as string}</span>
            <p className={styles.readonlyValue}>
              <BotStatusBadge status={bot.status} />
            </p>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>{t("dashboard.botDetail.lastUpdated") as string}</span>
            <p className={styles.readonlyValue}>{formatDashboardDateTime(bot.updated_at)}</p>
          </div>
        </div>
      </section>

      <form
        className={styles.card}
        onSubmit={(event) => void onSubmit(event)}
        data-testid="bot-detail-form"
        noValidate
      >
        <div className={styles.grid}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-name">
              {t("dashboard.botDetail.name") as string}
            </label>
            <input
              id="bot-name"
              className={styles.input}
              value={activeForm.name}
              onChange={(event) => setField("name", event.target.value)}
              minLength={2}
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-status">
              {t("dashboard.botDetail.status") as string}
            </label>
            <select
              id="bot-status"
              className={styles.select}
              value={activeForm.status}
              onChange={(event) => setField("status", event.target.value as FormState["status"])}
            >
              <option value="draft">{t("dashboard.botDetail.statusDraft") as string}</option>
              <option value="active">{t("dashboard.botDetail.statusActive") as string}</option>
              <option value="paused">{t("dashboard.botDetail.statusPaused") as string}</option>
              <option value="archived">{t("dashboard.botDetail.statusArchived") as string}</option>
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-tone">
              {t("dashboard.botDetail.tone") as string}
            </label>
            <input
              id="bot-tone"
              className={styles.input}
              value={activeForm.tone}
              onChange={(event) => setField("tone", event.target.value)}
              placeholder={t("dashboard.botDetail.tonePlaceholder") as string}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-language">
              {t("dashboard.botDetail.language") as string}
            </label>
            <input
              id="bot-language"
              className={styles.input}
              value={activeForm.language}
              onChange={(event) => setField("language", event.target.value)}
              placeholder={t("dashboard.botDetail.languagePlaceholder") as string}
            />
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="bot-welcome-message">
            {t("dashboard.botDetail.welcomeMessage") as string}
          </label>
          <textarea
            id="bot-welcome-message"
            className={styles.textarea}
            value={activeForm.welcomeMessage}
            onChange={(event) => setField("welcomeMessage", event.target.value)}
            placeholder={t("dashboard.botDetail.welcomePlaceholder") as string}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="bot-short-description">
            {t("dashboard.botDetail.shortDescription") as string}
          </label>
          <textarea
            id="bot-short-description"
            className={styles.textarea}
            value={activeForm.shortDescription}
            onChange={(event) => setField("shortDescription", event.target.value)}
            placeholder={t("dashboard.botDetail.shortDescPlaceholder") as string}
          />
        </div>

        <h3 className={styles.sectionTitle}>{t("dashboard.botDetail.aiResponseTitle") as string}</h3>
        <p className={styles.fieldHint}>
          {t("dashboard.botDetail.aiResponseHint") as string}
        </p>

        <div className={styles.grid}>
          <div className={styles.field}>
            <span className={styles.label}>{t("dashboard.botDetail.inferenceProvider") as string}</span>
            <p className={styles.readonlyValue}>{inferenceProviderLabel(bot.provider_name)}</p>
            <p className={styles.fieldHint}>{t("dashboard.botDetail.inferenceProviderHint") as string}</p>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-model-name">
              {t("dashboard.botDetail.model") as string}
            </label>
            <input
              id="bot-model-name"
              className={styles.input}
              value={activeForm.modelName}
              onChange={(event) => setField("modelName", event.target.value)}
              placeholder={t("dashboard.botDetail.modelPlaceholder") as string}
              autoComplete="off"
              spellCheck={false}
              data-testid="bot-detail-model-name"
            />
            <p className={styles.fieldHint}>{t("dashboard.botDetail.modelHint") as string}</p>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-temperature">
              {t("dashboard.botDetail.temperature") as string}
            </label>
            <input
              id="bot-temperature"
              className={styles.input}
              type="number"
              min={0}
              max={2}
              step={0.05}
              value={activeForm.temperatureText}
              onChange={(event) => setField("temperatureText", event.target.value)}
              placeholder={t("dashboard.botDetail.defaultPlaceholder") as string}
              data-testid="bot-detail-temperature"
            />
            <p className={styles.fieldHint}>{t("dashboard.botDetail.temperatureHint") as string}</p>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="bot-max-tokens">
              {t("dashboard.botDetail.maxTokens") as string}
            </label>
            <input
              id="bot-max-tokens"
              className={styles.input}
              type="number"
              min={1}
              max={8192}
              step={1}
              value={activeForm.maxOutputTokensText}
              onChange={(event) => setField("maxOutputTokensText", event.target.value)}
              placeholder={t("dashboard.botDetail.defaultPlaceholder") as string}
              data-testid="bot-detail-max-output-tokens"
            />
            <p className={styles.fieldHint}>{t("dashboard.botDetail.maxTokensHint") as string}</p>
          </div>
        </div>

        {clientError || saveError ? (
          <p className={styles.errorBanner} role="alert" data-testid="bot-detail-save-error">
            {clientError ?? saveError}
          </p>
        ) : null}
        {saveSuccess ? (
          <p className={styles.successBanner} role="status" aria-live="polite" data-testid="bot-detail-save-success">
            {saveSuccess}
          </p>
        ) : null}

        {isArchiveConfirmOpen ? (
          <div className={styles.archiveConfirm} role="alertdialog" aria-label="Archive confirmation">
            <p className={styles.archiveConfirmText}>
              {t("dashboard.botDetail.archiveConfirmText") as string}
            </p>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.archiveDangerBtn}
                onClick={() => {
                  void (async () => {
                    await archive();
                    setIsArchiveConfirmOpen(false);
                  })();
                }}
                disabled={isArchiving}
                data-testid="bot-detail-archive-confirm-btn"
              >
                {isArchiving ? (t("dashboard.botDetail.archiving") as string) : (t("dashboard.botDetail.confirmArchive") as string)}
              </button>
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={() => setIsArchiveConfirmOpen(false)}
                disabled={isArchiving}
                data-testid="bot-detail-archive-cancel-btn"
              >
                {t("dashboard.botDetail.cancel") as string}
              </button>
            </div>
          </div>
        ) : null}

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.saveBtn}
            disabled={isSaving || isArchiving}
            data-testid="bot-detail-save-btn"
          >
            {isSaving ? (t("dashboard.botDetail.saving") as string) : (t("dashboard.botDetail.saveChanges") as string)}
          </button>
          <button
            type="button"
            className={styles.archiveBtn}
            onClick={() => setIsArchiveConfirmOpen(true)}
            disabled={isArchiving || isSaving || isDeleting || bot.status === "archived"}
            data-testid="bot-detail-archive-btn"
          >
            {bot.status === "archived" ? (t("dashboard.botDetail.alreadyArchived") as string) : (t("dashboard.botDetail.archiveBot") as string)}
          </button>
          <button
            type="button"
            className={styles.archiveDangerBtn}
            onClick={() => setIsDeleteConfirmOpen(true)}
            disabled={isArchiving || isSaving || isDeleting}
            data-testid="bot-detail-delete-btn"
          >
            {t("dashboard.botDetail.deletePermanently") as string}
          </button>
        </div>

        {isDeleteConfirmOpen ? (
          <div className={styles.archiveConfirm} role="alertdialog" aria-label="Delete confirmation">
            <p className={styles.archiveConfirmText}>
              {t("dashboard.botDetail.deleteConfirmText") as string}
            </p>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.archiveDangerBtn}
                onClick={() => {
                  void (async () => {
                    const ok = await hardDelete();
                    if (ok && typeof window !== "undefined") {
                      window.location.assign("/dashboard/bots");
                    }
                    setIsDeleteConfirmOpen(false);
                  })();
                }}
                disabled={isDeleting}
              >
                {isDeleting ? (t("dashboard.botDetail.deleting") as string) : (t("dashboard.botDetail.confirmDelete") as string)}
              </button>
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={() => setIsDeleteConfirmOpen(false)}
                disabled={isDeleting}
              >
                {t("dashboard.botDetail.cancel") as string}
              </button>
            </div>
          </div>
        ) : null}
      </form>

      <section className={styles.card} aria-label="Test chat">
        {bot.status === "archived" ? (
          <p className={styles.rowMeta} data-testid="bot-test-chat-archived-notice">
            {t("dashboard.botDetail.testChatArchived") as string}
          </p>
        ) : (
          <BotTestChatPanel botId={botId} goalType={bot.goal_type} />
        )}
      </section>
        </>
      ) : null}
    </div>
  );
}
