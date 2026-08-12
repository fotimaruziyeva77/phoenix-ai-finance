"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  listWebhookLogs,
  retryWebhook,
  type WebhookLogDto,
  type WebhookLogListResponseDto,
} from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

const STATUS_CLASS: Record<string, string> = {
  received: "badgeWarn",
  processed: "badgeOk",
  failed: "badgeBad",
};

const SOURCE_CLASS: Record<string, string> = {
  stripe: "badgeOk",
  telegram: "badgeMuted",
};

const PAGE_SIZE = 50;

export function SuperadminWebhookLogs() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const sw = (key: string) => String(t(`superadmin.webhooks.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const [items, setItems] = useState<WebhookLogDto[]>([]);
  const [total, setTotal] = useState(0);
  const [failedTotal, setFailedTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sinceFilter, setSinceFilter] = useState("");
  const [untilFilter, setUntilFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedLog, setExpandedLog] = useState<WebhookLogDto | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  async function load(off = offset) {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res: WebhookLogListResponseDto = await listWebhookLogs(token, {
        source: sourceFilter || undefined,
        status: statusFilter || undefined,
        since: sinceFilter || undefined,
        until: untilFilter || undefined,
        limit: PAGE_SIZE,
        offset: off,
      });
      setItems(res.items);
      setTotal(res.total);
      setFailedTotal(res.failed_total);
    } catch {
      setError(sw("loadError"));
    } finally {
      setLoading(false);
    }
  }

  async function handleRetry(logId: string) {
    if (!token) return;
    setRetrying(logId);
    try {
      const updated = await retryWebhook(token, logId);
      setItems(prev => prev.map(item => (item.id === logId ? updated : item)));
    } catch {
      setError("Failed to retry webhook.");
    } finally {
      setRetrying(null);
    }
  }

  useEffect(() => { void load(0); setOffset(0); }, [token, sourceFilter, statusFilter, sinceFilter, untilFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}

      {failedTotal > 0 && (
        <p className={styles.errorBanner} style={{ fontWeight: 600 }}>
          ⚠ {failedTotal} {sw("failedTotal")}
          {statusFilter !== "failed" && (
            <button
              style={{ marginLeft: "0.75rem", fontSize: "0.78rem", textDecoration: "underline", background: "none", border: "none", cursor: "pointer", color: "inherit" }}
              onClick={() => setStatusFilter("failed")}
            >
              {sw("showFailedOnly")}
            </button>
          )}
        </p>
      )}

      <div className={styles.toolbar} style={{ flexWrap: "wrap", gap: "0.5rem" }}>
        <select className={styles.filterInput} value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
          <option value="">{sw("allSources")}</option>
          <option value="stripe">{sw("stripe")}</option>
          <option value="telegram">{sw("telegram")}</option>
        </select>
        <select className={styles.filterInput} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">{sw("allStatuses")}</option>
          <option value="received">{sw("received")}</option>
          <option value="processed">{sw("processed")}</option>
          <option value="failed">{sw("failed")}</option>
        </select>
        <input
          type="datetime-local"
          className={styles.filterInput}
          title="Since"
          value={sinceFilter}
          onChange={e => setSinceFilter(e.target.value)}
          style={{ fontSize: "0.8rem" }}
        />
        <input
          type="datetime-local"
          className={styles.filterInput}
          title="Until"
          value={untilFilter}
          onChange={e => setUntilFilter(e.target.value)}
          style={{ fontSize: "0.8rem" }}
        />
        {(sinceFilter || untilFilter) && (
          <button className={styles.btnNeutral} style={{ fontSize: "0.78rem" }} onClick={() => { setSinceFilter(""); setUntilFilter(""); }}>
            {sw("clearDates")}
          </button>
        )}
        <span className={styles.toolbarMeta}>{total} {sw("logsCount")}</span>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>{sw("source")}</th>
              <th className={styles.th}>{sw("eventType")}</th>
              <th className={styles.th}>{sw("status")}</th>
              <th className={styles.th}>{sw("bot")}</th>
              <th className={styles.th}>{sw("receivedAt")}</th>
              <th className={styles.th}>{sw("details")}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sc("loading")}</td></tr>
            ) : items.length === 0 ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sw("noLogs")}</td></tr>
            ) : items.map(log => (
              <tr key={log.id} className={styles.row}>
                <td className={styles.td}>
                  <span className={styles[(SOURCE_CLASS[log.source] ?? "badge") as keyof typeof styles] as string}>
                    {log.source}
                  </span>
                </td>
                <td className={styles.td} style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                  {log.event_type ?? "—"}
                </td>
                <td className={styles.td}>
                  <span className={styles[(STATUS_CLASS[log.status] ?? "badge") as keyof typeof styles] as string}>
                    {log.status}
                  </span>
                  {log.error_message && (
                    <p className={styles.cellSub} style={{ color: "#c0392b" }}>{log.error_message.slice(0, 60)}</p>
                  )}
                </td>
                <td className={styles.td} style={{ fontFamily: "monospace", fontSize: "0.7rem" }}>
                  {log.bot_id ? log.bot_id.slice(0, 8) + "…" : "—"}
                </td>
                <td className={styles.td} style={{ whiteSpace: "nowrap" }}>
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className={styles.td}>
                  {log.payload_preview && (
                    <button className={styles.actionBtn} onClick={() => setExpandedLog(log)}>{sw("view")}</button>
                  )}
                  {log.status === "failed" && (
                    <button
                      className={styles.actionBtn}
                      disabled={retrying === log.id}
                      onClick={() => handleRetry(log.id)}
                      style={{ marginLeft: "0.35rem" }}
                    >
                      {retrying === log.id ? "..." : "Retry"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className={styles.toolbar}>
          <button className={styles.pageBtn} disabled={offset === 0} onClick={() => { const o = Math.max(0, offset - PAGE_SIZE); setOffset(o); void load(o); }}>← Prev</button>
          <span style={{ fontSize: "0.8125rem", color: "var(--bf-text-muted)" }}>Page {currentPage} / {totalPages}</span>
          <button className={styles.pageBtn} disabled={offset + PAGE_SIZE >= total} onClick={() => { const o = offset + PAGE_SIZE; setOffset(o); void load(o); }}>Next →</button>
        </div>
      )}

      {/* Payload drawer */}
      {expandedLog && (
        <div className={styles.modalOverlay} onClick={() => setExpandedLog(null)}>
          <div className={styles.modal} style={{ width: "min(36rem, 100%)", maxHeight: "80vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{expandedLog.source} — {expandedLog.event_type ?? "webhook"}</h3>
            <p className={styles.modalHint}>{new Date(expandedLog.created_at).toLocaleString()}</p>
            {expandedLog.error_message && (
              <p className={styles.errorBanner} style={{ marginBottom: "0.65rem" }}>{expandedLog.error_message}</p>
            )}
            <pre style={{ margin: 0, padding: "0.75rem", borderRadius: "8px", background: "var(--bf-page-bg)", border: "1px solid color-mix(in srgb, var(--bf-border) 70%, transparent)", fontSize: "0.75rem", overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              {JSON.stringify(expandedLog.payload_preview, null, 2)}
            </pre>
            <div className={styles.modalActions} style={{ marginTop: "0.75rem" }}>
              <button className={styles.btnNeutral} onClick={() => setExpandedLog(null)}>{sw("close")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
