"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import {
  type AdminAuditLogItemDto,
  type AdminAuditLogMetaDto,
  getAdminAuditLogMeta,
  listAdminAuditLogs,
} from "@/lib/api/platform-admin";

import styles from "@/components/superadmin/superadmin.module.css";

const ACTION_COLORS: Record<string, string> = {
  user_suspended:           "#fee2e2",
  user_unsuspended:         "#d1fae5",
  bot_platform_suspended:   "#fee2e2",
  bot_platform_unsuspended: "#d1fae5",
  bot_created:              "#dbeafe",
  bot_updated:              "#fef3c7",
  bot_archived:             "#f3f4f6",
  superadmin_tenant_inspect:"#ede9fe",
};

function fmtDate(s: string) {
  return new Date(s).toLocaleString("ru-RU", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export function SuperadminAuditLog() {
  const { accessToken } = useAuth();
  const { t } = useLanguage();

  const sa = useCallback((key: string) => String(t(`superadmin.auditLog.${key}`)), [t]);
  const sc = useCallback((key: string) => String(t(`superadmin.common.${key}`)), [t]);

  const [items, setItems]     = useState<AdminAuditLogItemDto[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [meta, setMeta]       = useState<AdminAuditLogMetaDto | null>(null);

  // filters
  const [actionFilter, setActionFilter]         = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [sinceFilter, setSinceFilter]           = useState("");
  const [offset, setOffset]                     = useState(0);
  const limit = 50;

  // snapshot drawer
  const [drawerItem, setDrawerItem] = useState<AdminAuditLogItemDto | null>(null);

  // load meta (dropdowns) once
  useEffect(() => {
    if (!accessToken) return;
    getAdminAuditLogMeta(accessToken)
      .then(setMeta)
      .catch(() => null);
  }, [accessToken]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAdminAuditLogs(accessToken, {
        limit,
        offset,
        action:      actionFilter || undefined,
        entity_type: entityTypeFilter || undefined,
        since:       sinceFilter || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setLoading(false);
    }
  }, [accessToken, offset, actionFilter, entityTypeFilter, sinceFilter, sc]);

  useEffect(() => { void load(); }, [load]);

  const pages = Math.ceil(total / limit);
  const page  = Math.floor(offset / limit);

  function resetFilters() {
    setActionFilter("");
    setEntityTypeFilter("");
    setSinceFilter("");
    setOffset(0);
  }

  return (
    <div>
      {/* Filters */}
      <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", marginBottom: "1rem", alignItems: "center" }}>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }}
          className={styles.filterInput}
        >
          <option value="">{sc("allActions")}</option>
          {meta?.actions.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>

        <select
          value={entityTypeFilter}
          onChange={(e) => { setEntityTypeFilter(e.target.value); setOffset(0); }}
          className={styles.filterInput}
        >
          <option value="">{sc("allTypes")}</option>
          {meta?.entity_types.map((et) => (
            <option key={et} value={et}>{et}</option>
          ))}
        </select>

        <input
          type="datetime-local"
          value={sinceFilter}
          onChange={(e) => { setSinceFilter(e.target.value ? new Date(e.target.value).toISOString() : ""); setOffset(0); }}
          className={styles.filterInput}
          title={sa("sinceDate")}
        />

        {(actionFilter || entityTypeFilter || sinceFilter) && (
          <button onClick={resetFilters} className={styles.pageBtn} style={{ color: "#dc2626" }}>
            {sc("clear")} ✕
          </button>
        )}

        <span style={{ marginLeft: "auto", fontSize: "0.85rem", color: "var(--bf-text-muted)", alignSelf: "center" }}>
          {sc("total")}: <strong>{total}</strong>
        </span>
      </div>

      {error && <p className={styles.errorBanner}>{error}</p>}

      {loading ? (
        <p style={{ color: "var(--bf-text-muted)" }}>{sc("loading")}</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>{sa("time")}</th>
                <th className={styles.th}>{sa("action")}</th>
                <th className={styles.th}>{sa("entityType")}</th>
                <th className={styles.th}>{sa("actor")}</th>
                <th className={styles.th}>{sa("meta")}</th>
                <th className={styles.th}>{sa("snapshot")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className={styles.row}>
                  <td className={styles.td} style={{ fontSize: "0.78rem", whiteSpace: "nowrap" }}>
                    {fmtDate(item.created_at)}
                  </td>
                  <td className={styles.td}>
                    <span style={{
                      background: ACTION_COLORS[item.action] ?? "#f3f4f6",
                      // Backgrounds are light pastels; force dark text so the label is readable
                      // (the dark-theme default --bf-text is near-white and vanished here).
                      color: "#1f2937",
                      borderRadius: 5,
                      padding: "2px 7px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}>
                      {item.action}
                    </span>
                  </td>
                  <td className={styles.td} style={{ fontSize: "0.75rem" }}>
                    <span style={{ fontWeight: 600 }}>{item.entity_type}</span>
                    <div style={{ color: "var(--bf-text-muted)", fontFamily: "monospace", fontSize: "0.7rem" }}>
                      {item.entity_id.slice(0, 8)}…
                    </div>
                  </td>
                  <td className={styles.td} style={{ fontSize: "0.78rem" }}>
                    {item.actor_email ? (
                      <Link href={`/superadmin/users/${item.actor_user_id}`} style={{ color: "var(--bf-accent)" }}>
                        {item.actor_email}
                      </Link>
                    ) : (
                      <span style={{ fontFamily: "monospace", color: "var(--bf-text-muted)", fontSize: "0.7rem" }}>
                        {item.actor_user_id.slice(0, 8)}…
                      </span>
                    )}
                  </td>
                  <td className={styles.td} style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)", maxWidth: 160 }}>
                    {item.metadata_json
                      ? Object.entries(item.metadata_json)
                          .slice(0, 2)
                          .map(([k, v]) => `${k}: ${String(v).slice(0, 30)}`)
                          .join(" · ")
                      : "—"}
                  </td>
                  <td className={styles.td}>
                    {(item.before_snapshot ?? item.after_snapshot) ? (
                      <button
                        className={styles.actionBtn}
                        onClick={() => setDrawerItem(item)}
                        style={{ fontSize: "0.72rem", padding: "2px 8px" }}
                      >
                        {sc("view")}
                      </button>
                    ) : "—"}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "2rem", color: "var(--bf-text-muted)" }}>
                    {sc("noRecords")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", justifyContent: "center" }}>
          <button className={styles.pageBtn} disabled={page === 0} onClick={() => setOffset(0)}>«</button>
          <button className={styles.pageBtn} disabled={page === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>‹</button>
          <span style={{ alignSelf: "center", fontSize: "0.85rem" }}>{page + 1} / {pages}</span>
          <button className={styles.pageBtn} disabled={page >= pages - 1} onClick={() => setOffset(offset + limit)}>›</button>
          <button className={styles.pageBtn} disabled={page >= pages - 1} onClick={() => setOffset((pages - 1) * limit)}>»</button>
        </div>
      )}

      {/* Snapshot drawer */}
      {drawerItem && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "var(--bf-surface)", borderRadius: 12, padding: "1.5rem",
            width: "min(580px, 95vw)", maxHeight: "85vh", overflow: "auto",
            boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>
                {sa("snapshotTitle")} — <code style={{ fontSize: "0.85rem" }}>{drawerItem.action}</code>
              </h3>
              <button
                onClick={() => setDrawerItem(null)}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem" }}
              >✕</button>
            </div>

            {drawerItem.before_snapshot && (
              <div style={{ marginBottom: "1rem" }}>
                <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "#dc2626", marginBottom: "0.25rem" }}>{sa("before")}</p>
                <pre style={{
                  background: "var(--bf-page-bg)", borderRadius: 8, padding: "0.75rem",
                  fontSize: "0.72rem", overflow: "auto", maxHeight: 200,
                }}>
                  {JSON.stringify(drawerItem.before_snapshot, null, 2)}
                </pre>
              </div>
            )}
            {drawerItem.after_snapshot && (
              <div>
                <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "#059669", marginBottom: "0.25rem" }}>{sa("after")}</p>
                <pre style={{
                  background: "var(--bf-page-bg)", borderRadius: 8, padding: "0.75rem",
                  fontSize: "0.72rem", overflow: "auto", maxHeight: 200,
                }}>
                  {JSON.stringify(drawerItem.after_snapshot, null, 2)}
                </pre>
              </div>
            )}
            {drawerItem.metadata_json && (
              <div style={{ marginTop: "1rem" }}>
                <p style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--bf-text-muted)", marginBottom: "0.25rem" }}>{sa("metadata")}</p>
                <pre style={{
                  background: "var(--bf-page-bg)", borderRadius: 8, padding: "0.75rem",
                  fontSize: "0.72rem", overflow: "auto", maxHeight: 120,
                }}>
                  {JSON.stringify(drawerItem.metadata_json, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
