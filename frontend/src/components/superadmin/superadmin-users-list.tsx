"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  listAdminUsers,
  bulkUserAction,
  type AdminUserListItemDto,
} from "@/lib/api/platform-admin";
import { parseApiErrorMessage } from "@/lib/api/errors";
import { formatDashboardDateTime } from "@/lib/format/datetime";

import styles from "./superadmin.module.css";

const PAGE = 25;

export function SuperadminUsersList() {
  const { t } = useLanguage();
  const su = (key: string) => String(t(`superadmin.users.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));
  const { accessToken, hydrated, canUseAuthenticatedApi } = useAuth();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<AdminUserListItemDto[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState("suspend");
  const [bulkReason, setBulkReason] = useState("");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [showBulkConfirm, setShowBulkConfirm] = useState(false);

  const load = useCallback(async () => {
    if (!canUseAuthenticatedApi) return;
    setLoading(true);
    setError(null);
    setSelected(new Set());
    try {
      const res = await listAdminUsers(accessToken, {
        limit: PAGE,
        offset,
        search: search || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(parseApiErrorMessage(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, offset, search, canUseAuthenticatedApi]);

  useEffect(() => {
    if (!hydrated || !canUseAuthenticatedApi) return;
    void load();
  }, [hydrated, canUseAuthenticatedApi, load]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setOffset(0);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const end = Math.min(offset + items.length, total);
  const canPrev = offset > 0;
  const canNext = offset + PAGE < total;

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map(u => u.id)));
    }
  }

  function toggleOne(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function handleBulkAction() {
    if (!accessToken || selected.size === 0) return;
    setBulkLoading(true);
    setError(null);
    try {
      const res = await bulkUserAction(accessToken, {
        action: bulkAction,
        user_ids: Array.from(selected),
        reason: bulkReason || null,
      });
      setSuccess(`${su("bulkSuccess")}: ${res.succeeded}/${res.failed}`);
      setTimeout(() => setSuccess(null), 4000);
      setSelected(new Set());
      setShowBulkConfirm(false);
      setBulkReason("");
      await load();
    } catch (e) {
      setError(parseApiErrorMessage(e));
    } finally {
      setBulkLoading(false);
    }
  }

  return (
    <div className={styles.stack}>
      <p className={styles.pageIntro}>{su("intro")}</p>
      {error ? <p className={styles.errorBanner}>{error}</p> : null}
      {success ? <p className={styles.successBanner}>{success}</p> : null}

      <div className={styles.toolbar}>
        <input
          type="text"
          className={styles.filterInput}
          placeholder={su("email") + " / " + su("name") + "..."}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <span className={styles.toolbarMeta}>
          {loading ? sc("loading") : total ? `${su("showingRange")} ${offset + 1}–${end} / ${total}` : su("noUsers")}
        </span>

        {selected.size > 0 && (
          <>
            <span style={{ fontSize: "0.8rem", color: "var(--bf-text-muted)" }}>{selected.size} {su("selected")}</span>
            <select
              className={styles.filterInput}
              value={bulkAction}
              onChange={e => setBulkAction(e.target.value)}
            >
              <option value="suspend">{su("suspend")}</option>
              <option value="activate">{su("activate")}</option>
            </select>
            <button
              type="button"
              className={styles.btnDanger}
              disabled={bulkLoading}
              onClick={() => setShowBulkConfirm(true)}
            >
              {su("applyTo")} {selected.size}
            </button>
          </>
        )}

        <button type="button" className={styles.btnNeutral} disabled={!canPrev || loading} onClick={() => setOffset((o) => Math.max(0, o - PAGE))}>
          {su("previous")}
        </button>
        <button type="button" className={styles.btnNeutral} disabled={!canNext || loading} onClick={() => setOffset((o) => o + PAGE)}>
          {su("next")}
        </button>
      </div>

      <div className={styles.tableWrap} data-testid="superadmin-users-table">
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th} style={{ width: "2rem" }}>
                <input
                  type="checkbox"
                  checked={items.length > 0 && selected.size === items.length}
                  onChange={toggleAll}
                  title={su("selectAll")}
                />
              </th>
              <th className={styles.th}>{su("email")}</th>
              <th className={styles.th}>{su("role")}</th>
              <th className={styles.th}>{su("status")}</th>
              <th className={styles.th}>{su("bots")}</th>
              <th className={styles.th}>{su("updated")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id} className={styles.row} style={selected.has(u.id) ? { background: "color-mix(in srgb, var(--bf-accent) 6%, transparent)" } : {}}>
                <td className={styles.td}>
                  <input
                    type="checkbox"
                    checked={selected.has(u.id)}
                    onChange={() => toggleOne(u.id)}
                  />
                </td>
                <td className={styles.td}>
                  <Link href={`/superadmin/users/${u.id}`} className={styles.rowLink}>
                    {u.email}
                  </Link>
                  {u.full_name ? <div className={styles.cellSub}>{u.full_name}</div> : null}
                </td>
                <td className={styles.td}>{u.role}</td>
                <td className={styles.td}>
                  {!u.is_active ? (
                    <span className={styles.badgeBad}>{su("inactive")}</span>
                  ) : u.suspended_at ? (
                    <span className={styles.badgeWarn}>{su("suspended")}</span>
                  ) : (
                    <span className={styles.badgeOk}>{su("active")}</span>
                  )}
                </td>
                <td className={styles.td}>{u.bot_count}</td>
                <td className={`${styles.td} ${styles.cellSub}`}>{formatDashboardDateTime(u.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bulk Confirm Modal */}
      {showBulkConfirm && (
        <div className={styles.modalOverlay} onClick={() => setShowBulkConfirm(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{su("confirmBulkTitle")}</h3>
            <p className={styles.modalHint}>
              {su("confirmBulkHint")} <strong>{bulkAction}</strong> → <strong>{selected.size}</strong>
            </p>
            {bulkAction === "suspend" && (
              <>
                <label className={styles.modalFieldLabel}>{su("reasonOptional")}</label>
                <textarea
                  className={styles.textarea}
                  placeholder={su("reasonPlaceholder")}
                  value={bulkReason}
                  onChange={e => setBulkReason(e.target.value)}
                />
              </>
            )}
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setShowBulkConfirm(false)}>{sc("cancel")}</button>
              <button className={styles.btnDanger} disabled={bulkLoading} onClick={handleBulkAction}>
                {bulkLoading ? su("processing") : `${su("confirmAction")} ${bulkAction}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
