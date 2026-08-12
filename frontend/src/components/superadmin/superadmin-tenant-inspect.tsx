"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import { fetchTenantInspection, type AdminTenantInspectionDto } from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import styles from "./superadmin.module.css";

type Props = {
  userId: string;
};

export function SuperadminTenantInspect({ userId }: Props) {
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const { t } = useLanguage();
  const st = (key: string) => String(t(`superadmin.tenant.${key}`));
  const [data, setData] = useState<AdminTenantInspectionDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setError(null);
    try {
      const d = await fetchTenantInspection(accessToken, userId);
      setData(d);
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setData(null);
    }
  }, [accessToken, userId, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  if (!data && !error) {
    return <p className={styles.pageIntro}>{st("loadingInspection")}</p>;
  }

  if (!data) {
    return (
      <div className={styles.stack}>
        <p className={styles.errorBanner}>{error}</p>
        <Link href={`/superadmin/users/${userId}`} className={styles.backLink}>
          ← {st("backToUser")}
        </Link>
      </div>
    );
  }

  const { summary, ai_usage } = data;

  return (
    <div className={styles.stack}>
      <Link href={`/superadmin/users/${userId}`} className={styles.backLink}>
        ← {st("backToUser")}
      </Link>
      <p className={styles.pageIntro}>
        {st("intro")}
      </p>
      <div className={styles.cardGrid}>
        <div className={styles.statCard}>
          <p className={styles.statLabel}>{st("leads")}</p>
          <p className={styles.statValue}>{data.lead_count}</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statLabel}>{st("conversations")}</p>
          <p className={styles.statValue}>{data.conversation_count}</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statLabel}>{st("aiCalls")}</p>
          <p className={styles.statValue}>{ai_usage.total_calls}</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statLabel}>{st("aiFailures")}</p>
          <p className={styles.statValue}>{ai_usage.failed_calls}</p>
        </div>
        <div className={styles.statCard}>
          <p className={styles.statLabel}>{st("tokensWindow")}</p>
          <p className={styles.statValue}>{ai_usage.total_tokens}</p>
        </div>
      </div>

      <section>
        <p className={styles.statLabel}>{st("tenantSummary")}</p>
        <dl className={styles.detailGrid}>
          <dt className={styles.detailDt}>{st("email")}</dt>
          <dd className={styles.detailDd}>{summary.email}</dd>
          <dt className={styles.detailDt}>{st("role")}</dt>
          <dd className={styles.detailDd}>{summary.role}</dd>
          <dt className={styles.detailDt}>{st("active")}</dt>
          <dd className={styles.detailDd}>{summary.is_active ? st("yes") : st("no")}</dd>
          <dt className={styles.detailDt}>{st("botsProfile")}</dt>
          <dd className={styles.detailDd}>{summary.bot_count}</dd>
        </dl>
      </section>

      <section>
        <p className={styles.statLabel}>{st("channelMix")}</p>
        {data.channels.length === 0 ? (
          <p className={styles.pageIntro}>{st("noConversations")}</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>{st("channel")}</th>
                  <th className={styles.th}>{st("conversations")}</th>
                </tr>
              </thead>
              <tbody>
                {data.channels.map((c) => (
                  <tr key={c.channel}>
                    <td className={styles.td}>{c.channel}</td>
                    <td className={styles.td}>{c.conversation_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <p className={styles.statLabel}>{st("botsShown")} ({data.bots.length})</p>
        {data.bots.length === 0 ? (
          <p className={styles.pageIntro}>{st("noBotsForTenant")}</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>{st("bot")}</th>
                  <th className={styles.th}>{st("status")}</th>
                  <th className={styles.th}>{st("channels")}</th>
                </tr>
              </thead>
              <tbody>
                {data.bots.map((b) => (
                  <tr key={b.id}>
                    <td className={styles.td}>
                      <Link href={`/superadmin/bots/${b.id}`} className={styles.rowLink}>
                        {b.name}
                      </Link>
                      <div className={styles.cellSub}>
                        {b.niche_id} · {b.goal_type}
                      </div>
                    </td>
                    <td className={styles.td}>
                      <span className={styles.badgeMuted}>{b.status}</span>
                    </td>
                    <td className={styles.td}>
                      <div className={styles.inlineBadges}>
                        {b.widget_configured ? <span className={styles.badgeOk}>{st("widget")}</span> : null}
                        {b.telegram_connected ? <span className={styles.badgeOk}>{st("telegram")}</span> : null}
                        {!b.widget_configured && !b.telegram_connected ? <span className={styles.badgeMuted}>—</span> : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <p className={styles.statLabel}>{st("aiUsageWindow")}</p>
        <p className={styles.pageIntro}>
          {formatDashboardDateTime(ai_usage.period_start)} → {formatDashboardDateTime(ai_usage.period_end)} · Success{" "}
          {ai_usage.successful_calls} / Fail {ai_usage.failed_calls}
        </p>
      </section>

      <section>
        <p className={styles.statLabel}>{st("dailyRollup")}</p>
        {data.ai_daily_usage.length === 0 ? (
          <p className={styles.pageIntro}>{st("noDailyData")}</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>{st("date")}</th>
                  <th className={styles.th}>{st("requests")}</th>
                  <th className={styles.th}>{st("tokens")}</th>
                  <th className={styles.th}>{st("costUsd")}</th>
                </tr>
              </thead>
              <tbody>
                {data.ai_daily_usage.map((row) => (
                  <tr key={row.usage_date}>
                    <td className={styles.td}>{row.usage_date}</td>
                    <td className={styles.td}>{row.total_requests}</td>
                    <td className={styles.td}>{row.total_tokens}</td>
                    <td className={styles.td}>{row.total_cost_usd.toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <p className={styles.statLabel}>{st("recentErrors")}</p>
        {data.recent_ai_failures.length === 0 ? (
          <p className={styles.pageIntro}>{st("noFailedCalls")}</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>{st("when")}</th>
                  <th className={styles.th}>{st("bot")}</th>
                  <th className={styles.th}>{st("model")}</th>
                  <th className={styles.th}>{st("code")}</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_ai_failures.map((f, i) => (
                  <tr key={`${f.at}-${f.bot_id}-${i}`}>
                    <td className={styles.td}>{formatDashboardDateTime(f.at)}</td>
                    <td className={styles.td}>
                      <Link href={`/superadmin/bots/${f.bot_id}`} className={styles.rowLink}>
                        {f.bot_id.slice(0, 8)}…
                      </Link>
                    </td>
                    <td className={styles.td}>{f.model_name}</td>
                    <td className={styles.td}>{f.error_code ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
