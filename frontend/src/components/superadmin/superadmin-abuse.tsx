"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  getAbuseReport,
  bulkUserAction,
  type AbuseReportDto,
} from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

export function SuperadminAbuse() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const sa = (key: string) => String(t(`superadmin.abuse.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const [report, setReport] = useState<AbuseReportDto | null>(null);
  const [days, setDays] = useState(1);
  const [threshold, setThreshold] = useState(500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [suspendMsg, setSuspendMsg] = useState("");
  const [suspending, setSuspending] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await getAbuseReport(token, { threshold_calls: threshold, days, limit: 50 });
      setReport(res);
    } catch {
      setError(sa("loadError"));
    } finally {
      setLoading(false);
    }
  }

  // Auto-reload when token, days, or threshold change
  useEffect(() => { void load(); }, [token, days, threshold]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSuspend(userId: string, email: string) {
    if (!token) return;
    setSuspending(userId);
    setSuspendMsg("");
    try {
      const res = await bulkUserAction(token, {
        action: "suspend",
        user_ids: [userId],
        reason: "Automated abuse detection — high API usage",
      });
      if (res.succeeded > 0) setSuspendMsg(`${sa("suspendedUser")}: ${email}`);
      else setSuspendMsg(`${sa("failedToSuspend")}: ${res.results[0]?.error ?? "unknown"}`);
    } catch {
      setSuspendMsg(sa("suspendError"));
    } finally {
      setSuspending(null);
      setTimeout(() => setSuspendMsg(""), 4000);
    }
  }

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}
      {suspendMsg && <p className={styles.successBanner}>{suspendMsg}</p>}

      <div className={styles.toolbar}>
        <label style={{ fontSize: "0.8125rem", color: "var(--bf-text-muted)" }}>
          {sa("periodLabel")}
          <select className={styles.filterInput} style={{ marginLeft: "0.35rem" }} value={days} onChange={e => setDays(+e.target.value)}>
            <option value={1}>{sa("day1")}</option>
            <option value={3}>{sa("day3")}</option>
            <option value={7}>{sa("day7")}</option>
          </select>
        </label>
        <label style={{ fontSize: "0.8125rem", color: "var(--bf-text-muted)" }}>
          {sa("minCalls")}
          <select className={styles.filterInput} style={{ marginLeft: "0.35rem" }} value={threshold} onChange={e => setThreshold(+e.target.value)}>
            <option value={100}>100</option>
            <option value={500}>500</option>
            <option value={1000}>1 000</option>
            <option value={5000}>5 000</option>
          </select>
        </label>
        <button className={styles.btnPrimary} disabled={loading} onClick={load}>
          {loading ? sc("loading") : sa("refresh")}
        </button>
      </div>

      <section>
        <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>
          {sa("highUsageTitle")} (≥{threshold} / {days}d)
        </h3>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>{sa("user")}</th>
                <th className={styles.th}>{sa("calls")}</th>
                <th className={styles.th}>{sa("failed")}</th>
                <th className={styles.th}>{sa("tokens")}</th>
                <th className={styles.th}>{sa("cost")}</th>
                <th className={styles.th}>{sa("errorRate")}</th>
                <th className={styles.th}>{sa("actions")}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className={styles.td} colSpan={7} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sc("loading")}</td></tr>
              ) : !report || report.high_usage.length === 0 ? (
                <tr><td className={styles.td} colSpan={7} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sa("noHighUsage")}</td></tr>
              ) : report.high_usage.map(u => (
                <tr key={u.owner_id} className={styles.row}>
                  <td className={styles.td}>
                    <Link href={`/superadmin/users/${u.owner_id}`} className={styles.rowLink}>{u.owner_email}</Link>
                  </td>
                  <td className={styles.td} style={{ fontWeight: 700 }}>{u.total_calls.toLocaleString()}</td>
                  <td className={styles.td} style={{ color: u.failed_calls > 0 ? "#c0392b" : undefined }}>{u.failed_calls}</td>
                  <td className={styles.td}>{u.total_tokens.toLocaleString()}</td>
                  <td className={styles.td}>${Number(u.total_cost_usd).toFixed(4)}</td>
                  <td className={styles.td}>
                    <span className={u.error_rate > 0.1 ? styles.badgeBad : u.error_rate > 0.05 ? styles.badgeWarn : styles.badgeOk}>
                      {(u.error_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className={styles.td}>
                    <button
                      className={styles.btnDanger}
                      style={{ fontSize: "0.78rem", padding: "3px 10px" }}
                      disabled={suspending === u.owner_id}
                      onClick={() => handleSuspend(u.owner_id, u.owner_email)}
                    >
                      {suspending === u.owner_id ? "…" : sa("suspend")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 style={{ margin: "0 0 0.65rem", fontSize: "0.9rem", fontWeight: 700 }}>
          {sa("topErrorsTitle")} ({days}d)
        </h3>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>{sa("user")}</th>
                <th className={styles.th}>{sa("errorCode")}</th>
                <th className={styles.th}>{sa("occurrences")}</th>
              </tr>
            </thead>
            <tbody>
              {!report || report.top_errors.length === 0 ? (
                <tr><td className={styles.td} colSpan={3} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sa("noErrors")}</td></tr>
              ) : report.top_errors.map((e, i) => (
                <tr key={i} className={styles.row}>
                  <td className={styles.td}>{e.owner_email}</td>
                  <td className={styles.td}><span className={styles.badgeBad}>{e.error_code}</span></td>
                  <td className={styles.td} style={{ fontWeight: 600 }}>{e.occurrences}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
