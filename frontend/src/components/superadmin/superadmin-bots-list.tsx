"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import { listAdminBots, bulkBotAction, type AdminBotListItemDto } from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import styles from "./superadmin.module.css";

const PAGE = 25;

export function SuperadminBotsList() {
  const { t } = useLanguage();
  const sb = (key: string) => String(t(`superadmin.botsList.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<AdminBotListItemDto[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showBulk, setShowBulk] = useState(false);
  const [bulkAction, setBulkAction] = useState<"suspend" | "activate">("suspend");
  const [bulkReason, setBulkReason] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResult, setBulkResult] = useState<string | null>(null);

  useEffect(() => {
    const id = setTimeout(() => setSearch(searchInput), 400);
    return () => clearTimeout(id);
  }, [searchInput]);

  // Reset to first page when filters change
  useEffect(() => {
    setOffset(0);
  }, [search, statusFilter]);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setLoading(true);
    setError(null);
    setSelected(new Set());
    try {
      const res = await listAdminBots(accessToken, {
        limit: PAGE,
        offset,
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, offset, search, statusFilter, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  const end = Math.min(offset + items.length, total);
  const canPrev = offset > 0;
  const canNext = offset + PAGE < total;

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map(b => b.id)));
    }
  }

  async function handleBulkAction() {
    if (!accessToken) return;
    setBulkRunning(true);
    setBulkResult(null);
    try {
      const res = await bulkBotAction(accessToken, {
        action: bulkAction,
        bot_ids: Array.from(selected),
        reason: bulkAction === "suspend" ? bulkReason || null : null,
      });
      setBulkResult(`${res.succeeded} succeeded, ${res.failed} failed`);
      setSelected(new Set());
      setShowBulk(false);
      setBulkReason("");
      void load();
    } catch (e) {
      setBulkResult(e instanceof Error ? e.message : "Error");
    } finally {
      setBulkRunning(false);
    }
  }

  return (
    <div className={styles.stack}>
      <p className={styles.pageIntro}>{sb("intro")}</p>
      {error ? <p className={styles.errorBanner}>{error}</p> : null}
      {bulkResult && <p className={styles.successBanner}>{bulkResult}</p>}
      <div className={styles.toolbar}>
        <input
          type="text"
          className={styles.filterInput}
          placeholder={sb("bot") + " / " + sb("owner") + "..."}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <select
          className={styles.filterInput}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{sb("status")}: --</option>
          <option value="draft">draft</option>
          <option value="active">active</option>
          <option value="paused">paused</option>
          <option value="archived">archived</option>
        </select>
        <span className={styles.toolbarMeta}>
          {loading ? sc("loading") : total ? `${sb("showingRange")} ${offset + 1}–${end} / ${total}` : sb("noBots")}
        </span>
        <button type="button" className={styles.btnNeutral} disabled={!canPrev || loading} onClick={() => setOffset((o) => Math.max(0, o - PAGE))}>
          {sb("previous")}
        </button>
        <button type="button" className={styles.btnNeutral} disabled={!canNext || loading} onClick={() => setOffset((o) => o + PAGE)}>
          {sb("next")}
        </button>
      </div>

      {selected.size > 0 && (
        <div className={styles.toolbar} style={{ background: "color-mix(in srgb, var(--bf-accent) 8%, transparent)", borderRadius: 8, padding: "0.5rem 0.75rem" }}>
          <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{selected.size} {sb("selected")}</span>
          <button className={styles.btnDanger} onClick={() => { setBulkAction("suspend"); setShowBulk(true); }}>
            {sb("bulkSuspend")}
          </button>
          <button className={styles.btnPrimary} onClick={() => { setBulkAction("activate"); setShowBulk(true); }}>
            {sb("bulkActivate")}
          </button>
        </div>
      )}

      <div className={styles.tableWrap} data-testid="superadmin-bots-table">
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th} style={{ width: "2rem" }}>
                <input
                  type="checkbox"
                  checked={items.length > 0 && selected.size === items.length}
                  onChange={toggleAll}
                />
              </th>
              <th className={styles.th}>{sb("bot")}</th>
              <th className={styles.th}>{sb("owner")}</th>
              <th className={styles.th}>{sb("status")}</th>
              <th className={styles.th}>{sb("channels")}</th>
              <th className={styles.th}>{sb("updated")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((b) => (
              <tr key={b.id} className={styles.row} style={selected.has(b.id) ? { background: "color-mix(in srgb, var(--bf-accent) 6%, transparent)" } : {}}>
                <td className={styles.td}>
                  <input
                    type="checkbox"
                    checked={selected.has(b.id)}
                    onChange={() => toggleSelect(b.id)}
                  />
                </td>
                <td className={styles.td}>
                  <Link href={`/superadmin/bots/${b.id}`} className={styles.rowLink}>
                    {b.name}
                  </Link>
                  <div className={styles.cellSub}>
                    {b.niche_id} · {b.goal_type}
                  </div>
                </td>
                <td className={styles.td}>
                  <div>{b.owner_email}</div>
                  <div className={styles.cellSub}>{b.owner_id}</div>
                </td>
                <td className={styles.td}>
                  <span className={styles.badgeMuted}>{b.status}</span>
                  {b.platform_suspended_at ? <span className={styles.badgeBad}> {sb("platformSuspended")}</span> : null}
                </td>
                <td className={styles.td}>
                  <div className={styles.inlineBadges}>
                    {b.widget_configured ? <span className={styles.badgeOk}>{sb("widget")}</span> : null}
                    {b.telegram_connected ? <span className={styles.badgeOk}>{sb("telegram")}</span> : null}
                    {!b.widget_configured && !b.telegram_connected ? <span className={styles.badgeMuted}>—</span> : null}
                  </div>
                </td>
                <td className={styles.td}>
                  <span className={styles.cellSub}>{formatDashboardDateTime(b.updated_at)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bulk Confirm Modal */}
      {showBulk && (
        <div className={styles.modalOverlay} onClick={() => setShowBulk(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>
              {bulkAction === "suspend" ? sb("bulkSuspendTitle") : sb("bulkActivateTitle")}
            </h3>
            <p className={styles.modalHint}>
              {sb("bulkApplyTo")} <strong>{selected.size}</strong> {sb("botsCount")}
            </p>
            {bulkAction === "suspend" && (
              <>
                <label className={styles.modalFieldLabel}>{sb("bulkReason")}</label>
                <textarea
                  className={styles.textarea}
                  value={bulkReason}
                  onChange={e => setBulkReason(e.target.value)}
                  placeholder={sb("bulkReasonPlaceholder")}
                />
              </>
            )}
            {bulkResult && <p style={{ fontSize: "0.82rem", color: "var(--bf-text-muted)", marginTop: "0.5rem" }}>{bulkResult}</p>}
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setShowBulk(false)}>
                {sc("cancel")}
              </button>
              <button
                className={bulkAction === "suspend" ? styles.btnDanger : styles.btnPrimary}
                disabled={bulkRunning}
                onClick={handleBulkAction}
              >
                {bulkRunning ? sc("loading") : (bulkAction === "suspend" ? sb("bulkSuspend") : sb("bulkActivate"))}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
