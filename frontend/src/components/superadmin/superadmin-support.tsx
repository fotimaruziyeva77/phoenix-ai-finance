"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  adminListTickets,
  adminUpdateTicket,
  type AdminTicketDto,
} from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

const STATUS_COLORS: Record<string, string> = {
  open: styles.badgeWarn ?? "",
  in_progress: styles.badgeOk ?? "",
  resolved: styles.badgeMuted ?? "",
  closed: styles.badgeMuted ?? "",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: styles.badgeMuted ?? "",
  normal: styles.badgeOk ?? "",
  high: styles.badgeBad ?? "",
};

const PAGE_SIZE = 25;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SuperadminSupport() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const ss = (key: string) => String(t(`superadmin.support.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const [items, setItems] = useState<AdminTicketDto[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [editTicket, setEditTicket] = useState<AdminTicketDto | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editPriority, setEditPriority] = useState("");
  const [editNote, setEditNote] = useState("");
  const [saving, setSaving] = useState(false);

  async function load(off = offset) {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await adminListTickets(token, {
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        limit: PAGE_SIZE,
        offset: off,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError(ss("loadError"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(0); setOffset(0); }, [token, statusFilter, priorityFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  function openEdit(ticket: AdminTicketDto) {
    setEditTicket(ticket);
    setEditStatus(ticket.status);
    setEditPriority(ticket.priority);
    setEditNote("");
  }

  async function handleSave(overrideStatus?: string) {
    if (!editTicket || !token) return;
    setSaving(true);
    try {
      const updated = await adminUpdateTicket(token, editTicket.id, {
        status: overrideStatus || editStatus || null,
        priority: editPriority || null,
        admin_note: editNote || null,
      });
      setItems(prev => prev.map(ticket => ticket.id === updated.id ? updated : ticket));
      setEditTicket(null);
    } catch {
      setError(ss("updateError"));
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}

      <div className={styles.toolbar}>
        <select
          className={styles.filterInput}
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">{ss("allStatuses")}</option>
          <option value="open">{ss("statusOpen")}</option>
          <option value="in_progress">{ss("statusInProgress")}</option>
          <option value="resolved">{ss("statusResolved")}</option>
          <option value="closed">{ss("statusClosed")}</option>
        </select>
        <select
          className={styles.filterInput}
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
        >
          <option value="">{ss("allPriorities")}</option>
          <option value="low">{ss("priorityLow")}</option>
          <option value="normal">{ss("priorityNormal")}</option>
          <option value="high">{ss("priorityHigh")}</option>
        </select>
        <span className={styles.toolbarMeta}>{total} {ss("ticketsCount")}</span>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>{ss("subject")}</th>
              <th className={styles.th}>{ss("user")}</th>
              <th className={styles.th}>{ss("status")}</th>
              <th className={styles.th}>{ss("priority")}</th>
              <th className={styles.th}>{ss("created")}</th>
              <th className={styles.th}>{ss("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sc("loading")}</td></tr>
            ) : items.length === 0 ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{ss("noTickets")}</td></tr>
            ) : items.map(ticket => (
              <tr key={ticket.id} className={styles.row} style={{ cursor: "pointer" }} onClick={() => openEdit(ticket)}>
                <td className={styles.td}>
                  <span style={{ fontWeight: 600 }}>{ticket.subject}</span>
                  {ticket.admin_note && <p className={styles.cellSub}>{ss("notePrefix")}{ticket.admin_note.slice(0, 60)}{ticket.admin_note.length > 60 ? "..." : ""}</p>}
                </td>
                <td className={styles.td}>{ticket.user_email}</td>
                <td className={styles.td}><span className={STATUS_COLORS[ticket.status] ?? styles.badge}>{ticket.status}</span></td>
                <td className={styles.td}><span className={PRIORITY_COLORS[ticket.priority] ?? styles.badge}>{ticket.priority}</span></td>
                <td className={styles.td} style={{ whiteSpace: "nowrap" }}>{new Date(ticket.created_at).toLocaleDateString()}</td>
                <td className={styles.td}>
                  <button className={styles.actionBtn} onClick={(e) => { e.stopPropagation(); openEdit(ticket); }}>{ss("edit")}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className={styles.toolbar}>
          <button className={styles.pageBtn} disabled={offset === 0} onClick={() => { const o = Math.max(0, offset - PAGE_SIZE); setOffset(o); load(o); }}>{`← ${ss("prevPage")}`}</button>
          <span style={{ fontSize: "0.8125rem", color: "var(--bf-text-muted)" }}>{ss("pageOf")} {currentPage} / {totalPages}</span>
          <button className={styles.pageBtn} disabled={offset + PAGE_SIZE >= total} onClick={() => { const o = offset + PAGE_SIZE; setOffset(o); load(o); }}>{`${ss("nextPage")} →`}</button>
        </div>
      )}

      {/* Ticket Detail / Reply Drawer */}
      {editTicket && (
        <div className={styles.modalOverlay} onClick={() => setEditTicket(null)}>
          <div
            className={styles.modal}
            style={{ width: "min(640px, 95vw)", maxHeight: "90vh", overflowY: "auto" }}
            onClick={e => e.stopPropagation()}
          >
            {/* Header: subject + badges */}
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <h3 className={styles.modalTitle} style={{ margin: 0, fontSize: "1.1rem" }}>
                {editTicket.subject}
              </h3>
              <div style={{ display: "flex", gap: "0.35rem", flexShrink: 0 }}>
                <span className={STATUS_COLORS[editTicket.status] ?? styles.badge}>{editTicket.status}</span>
                <span className={PRIORITY_COLORS[editTicket.priority] ?? styles.badge}>{editTicket.priority}</span>
              </div>
            </div>

            {/* Meta: user email + timestamps */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem 1.25rem", marginBottom: "1rem", fontSize: "0.8rem", color: "var(--bf-text-muted)" }}>
              <span>{editTicket.user_email}</span>
              <span>{ss("submittedAt")}: {formatTimestamp(editTicket.created_at)}</span>
              {editTicket.resolved_at && (
                <span>{ss("resolvedAt")}: {formatTimestamp(editTicket.resolved_at)}</span>
              )}
            </div>

            {/* Ticket body */}
            <label className={styles.modalFieldLabel}>{ss("ticketBody")}</label>
            <div style={{
              padding: "0.7rem 0.85rem",
              borderRadius: "10px",
              background: "color-mix(in srgb, var(--bf-page-bg) 80%, var(--bf-border))",
              border: "1px solid color-mix(in srgb, var(--bf-border) 60%, transparent)",
              fontSize: "0.8125rem",
              lineHeight: 1.55,
              maxHeight: "12rem",
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              marginBottom: "1rem",
            }}>
              {editTicket.body}
            </div>

            {/* Previous admin reply */}
            {editTicket.admin_note && (
              <>
                <label className={styles.modalFieldLabel}>{ss("previousReply")}</label>
                <div style={{
                  padding: "0.7rem 0.85rem",
                  borderRadius: "10px",
                  background: "color-mix(in srgb, var(--bf-accent) 8%, transparent)",
                  border: "1px solid color-mix(in srgb, var(--bf-accent) 25%, transparent)",
                  fontSize: "0.8125rem",
                  lineHeight: 1.55,
                  maxHeight: "8rem",
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  marginBottom: "1rem",
                }}>
                  {editTicket.admin_note}
                </div>
              </>
            )}

            {!editTicket.admin_note && (
              <p style={{ margin: "0 0 1rem", fontSize: "0.8rem", color: "var(--bf-text-muted)", fontStyle: "italic" }}>
                {ss("noReplyYet")}
              </p>
            )}

            {/* Divider */}
            <div style={{ borderTop: "1px solid color-mix(in srgb, var(--bf-border) 70%, transparent)", margin: "0.25rem 0 1rem" }} />

            {/* Status + Priority dropdowns (side by side) */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.85rem" }}>
              <div>
                <label className={styles.modalFieldLabel}>{ss("statusLabel")}</label>
                <select className={styles.filterInput} style={{ width: "100%" }} value={editStatus} onChange={e => setEditStatus(e.target.value)}>
                  <option value="open">{ss("statusOpen")}</option>
                  <option value="in_progress">{ss("statusInProgress")}</option>
                  <option value="resolved">{ss("statusResolved")}</option>
                  <option value="closed">{ss("statusClosed")}</option>
                </select>
              </div>
              <div>
                <label className={styles.modalFieldLabel}>{ss("priorityLabel")}</label>
                <select className={styles.filterInput} style={{ width: "100%" }} value={editPriority} onChange={e => setEditPriority(e.target.value)}>
                  <option value="low">{ss("priorityLow")}</option>
                  <option value="normal">{ss("priorityNormal")}</option>
                  <option value="high">{ss("priorityHigh")}</option>
                </select>
              </div>
            </div>

            {/* Reply textarea */}
            <label className={styles.modalFieldLabel}>{ss("replyLabel")}</label>
            <textarea
              className={styles.textarea}
              style={{ minHeight: "5.5rem" }}
              placeholder={ss("replyPlaceholder")}
              value={editNote}
              onChange={e => setEditNote(e.target.value)}
            />

            {/* Action buttons */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button className={styles.btnNeutral} onClick={() => setEditTicket(null)} disabled={saving}>
                {ss("cancel")}
              </button>
              <button className={styles.btnPrimary} disabled={saving} onClick={() => handleSave()}>
                {saving ? ss("saving") : ss("save")}
              </button>
              <button
                className={styles.btnPrimary}
                style={{ background: "color-mix(in srgb, #f39c12 18%, transparent)", borderColor: "color-mix(in srgb, #f39c12 45%, transparent)" }}
                disabled={saving || !editNote.trim()}
                onClick={() => handleSave("in_progress")}
              >
                {ss("replyAndProgress")}
              </button>
              <button
                className={styles.btnPrimary}
                style={{ background: "color-mix(in srgb, #27ae60 18%, transparent)", borderColor: "color-mix(in srgb, #27ae60 45%, transparent)" }}
                disabled={saving || !editNote.trim()}
                onClick={() => handleSave("resolved")}
              >
                {ss("replyAndResolve")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
