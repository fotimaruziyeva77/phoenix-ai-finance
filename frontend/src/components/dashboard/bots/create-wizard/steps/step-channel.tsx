import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { fetchSubscription } from "@/lib/api/billing";
import { CHANNEL_PLACEHOLDERS } from "@/lib/create-bot-wizard/options";
import type { CreateBotDraft } from "@/lib/create-bot-wizard/types";

import styles from "../create-bot-wizard.module.css";

type TFn = (key: string) => unknown;

type Props = {
  draft: CreateBotDraft;
  updateDraft: (fn: (d: CreateBotDraft) => CreateBotDraft) => void;
  t: TFn;
};

const CH_LABEL_KEYS: Record<string, string> = {
  website_widget: "dashboard.wizard.chWebsite",
  telegram: "dashboard.wizard.chTelegram",
  both: "dashboard.wizard.chBoth",
};
const CH_HINT_KEYS: Record<string, string> = {
  website_widget: "dashboard.wizard.chWebsiteHint",
  telegram: "dashboard.wizard.chTelegramHint",
  both: "dashboard.wizard.chBothHint",
};

function showTelegramFields(draft: CreateBotDraft): boolean {
  const id = draft.channel.preferredChannelId;
  return id === "telegram" || id === "both";
}

function requiresTelegram(channelId: string): boolean {
  return channelId === "telegram" || channelId === "both";
}

export function StepChannel({ draft, updateDraft, t }: Props) {
  const { accessToken } = useAuth();
  const [planSlug, setPlanSlug] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchSubscription(accessToken)
      .then((sub) => { if (alive) setPlanSlug(sub.plan_slug); })
      .catch(() => { if (alive) setPlanSlug("free"); });
    return () => { alive = false; };
  }, [accessToken]);

  const isFreePlan = planSlug === "free";

  return (
    <>
      <p className={styles.hintBox}>
        {t("dashboard.wizard.channelHint") as string}
      </p>
      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>{t("dashboard.wizard.channelLegend") as string}</legend>
        <div className={styles.grid} data-testid="channel-grid">
          {CHANNEL_PLACEHOLDERS.map((opt) => {
            const needsTelegram = requiresTelegram(opt.id);
            const locked = isFreePlan && needsTelegram;

            return (
              <label
                key={opt.id}
                className={styles.choice}
                data-testid={`channel-card-${opt.id}`}
                style={locked ? { opacity: 0.55, cursor: "not-allowed" } : undefined}
              >
                <input
                  className={styles.choiceInput}
                  type="radio"
                  name="channel"
                  value={opt.id}
                  checked={draft.channel.preferredChannelId === opt.id}
                  disabled={locked}
                  onChange={() =>
                    updateDraft((d) => ({
                      ...d,
                      channel: { ...d.channel, preferredChannelId: opt.id },
                    }))
                  }
                />
                <span
                  className={styles.choiceCard}
                  data-selected={draft.channel.preferredChannelId === opt.id ? "true" : "false"}
                >
                  <span className={styles.choiceLabel}>
                    {t(CH_LABEL_KEYS[opt.id] ?? "") as string}
                    {locked && (
                      <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--bf-accent)", marginLeft: "0.35rem" }}>
                        {t("dashboard.wizard.proPlus") as string}
                      </span>
                    )}
                  </span>
                  <p className={styles.choiceHint}>
                    {locked ? (t("dashboard.wizard.upgradeForTelegram") as string) : (t(CH_HINT_KEYS[opt.id] ?? "") as string)}
                  </p>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {isFreePlan && draft.channel.preferredChannelId && requiresTelegram(draft.channel.preferredChannelId) && (
        <div
          style={{
            padding: "0.85rem 1rem",
            borderRadius: "10px",
            border: "1px solid color-mix(in srgb, var(--bf-accent) 35%, var(--bf-border))",
            background: "color-mix(in srgb, var(--bf-accent) 6%, var(--bf-surface))",
            fontSize: "0.85rem",
            marginBottom: "0.75rem",
          }}
        >
          <strong>{t("dashboard.wizard.telegramRequiresPro") as string}</strong>{" "}
          <Link href="/dashboard/billing" style={{ color: "var(--bf-accent)", fontWeight: 600 }}>
            {t("dashboard.wizard.upgradeNow") as string}
          </Link>
        </div>
      )}

      {showTelegramFields(draft) && !isFreePlan ? (
        <div className={styles.fieldGroup} data-testid="telegram-token-section">
          <label className={styles.fieldLabel} htmlFor="telegram-bot-token">
            {t("dashboard.wizard.telegramToken") as string} <span className={styles.optionalTag}>({t("dashboard.wizard.optional") as string})</span>
          </label>
          <p className={styles.fieldHelp}>
            {t("dashboard.wizard.telegramTokenHelp") as string}
          </p>
          <input
            id="telegram-bot-token"
            className={styles.textInput}
            type="password"
            autoComplete="off"
            placeholder={t("dashboard.wizard.telegramTokenPlaceholder") as string}
            value={draft.channel.telegramBotToken ?? ""}
            onChange={(e) =>
              updateDraft((d) => ({
                ...d,
                channel: { ...d.channel, telegramBotToken: e.target.value },
              }))
            }
            data-testid="telegram-bot-token-input"
          />
        </div>
      ) : null}
    </>
  );
}
