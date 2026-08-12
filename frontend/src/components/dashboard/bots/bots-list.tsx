"use client";

import Link from "next/link";

import { useLanguage } from "@/contexts/language-context";
import type { WorkspaceBot } from "@/lib/api/bots";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import { BotStatusBadge } from "./bot-status-badge";
import styles from "./bots-dashboard.module.css";

type Props = {
  bots: WorkspaceBot[];
  onClone?: (botId: string) => void;
  cloningId?: string | null;
};

export function BotsList({ bots, onClone, cloningId }: Props) {
  const { t } = useLanguage();
  const cloneLabel = t("dashboard.bots.clone") as string;
  const cloningLabel = t("dashboard.bots.cloning") as string;

  return (
    <div className={styles.listShell} data-testid="bots-list-shell">
      <div className={styles.listTableWrap} role="region" aria-label="Bot list" data-testid="bots-list">
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colName") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colNiche") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colGoal") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colStatus") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colUpdated") as string}
              </th>
              <th scope="col" className={styles.th}>
                {t("dashboard.bots.colActions") as string}
              </th>
            </tr>
          </thead>
          <tbody>
            {bots.map((bot) => (
              <tr key={bot.id} className={styles.tr} data-testid="bots-list-row">
                <td className={styles.td}>
                  <Link href={`/dashboard/bots/${bot.id}`} className={styles.botName}>
                    {bot.name}
                  </Link>
                </td>
                <td className={`${styles.td} ${styles.tdMuted}`}>{bot.nicheLabel}</td>
                <td className={`${styles.td} ${styles.tdMuted}`}>{bot.goalLabel}</td>
                <td className={styles.td}>
                  <BotStatusBadge status={bot.status} />
                </td>
                <td className={`${styles.td} ${styles.tdMuted}`}>{formatDashboardDateTime(bot.updatedAt)}</td>
                <td className={styles.td}>
                  <button
                    className={styles.cloneBtn}
                    onClick={() => onClone?.(bot.id)}
                    disabled={Boolean(cloningId)}
                    aria-label={`${cloneLabel} ${bot.name}`}
                    data-testid="clone-bot-btn"
                  >
                    {cloningId === bot.id ? cloningLabel : cloneLabel}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className={styles.cardList} aria-label="Bot list (compact view)">
        {bots.map((bot) => (
          <li key={bot.id} className={styles.cardItem} data-testid="bots-list-card">
            <div className={styles.cardTop}>
              <Link href={`/dashboard/bots/${bot.id}`} className={styles.botName}>
                {bot.name}
              </Link>
              <div className={styles.cardTopRight}>
                <BotStatusBadge status={bot.status} />
                <button
                  className={styles.cloneBtn}
                  onClick={() => onClone?.(bot.id)}
                  disabled={Boolean(cloningId)}
                  aria-label={`${cloneLabel} ${bot.name}`}
                  data-testid="clone-bot-btn"
                >
                  {cloningId === bot.id ? cloningLabel : cloneLabel}
                </button>
              </div>
            </div>
            <dl className={styles.cardMeta}>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.bots.colNiche") as string}</dt>
                <dd>{bot.nicheLabel}</dd>
              </div>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.bots.colGoal") as string}</dt>
                <dd>{bot.goalLabel}</dd>
              </div>
              <div className={styles.cardRow}>
                <dt>{t("dashboard.bots.colUpdated") as string}</dt>
                <dd>{formatDashboardDateTime(bot.updatedAt)}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </div>
  );
}
