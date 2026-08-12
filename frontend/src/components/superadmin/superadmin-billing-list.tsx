"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import {
  type AdminBillingListItemDto,
  adminOverrideSubscription,
  listAdminBilling,
} from "@/lib/api/platform-admin";

import styles from "@/components/superadmin/superadmin.module.css";

const PLAN_PRICES: Record<string, number> = {
  free: 0, pro: 39, business: 99, enterprise: 0,
};

const PLAN_COLORS: Record<string, string> = {
  free: "#6b7280",
  pro: "#8b5cf6",
  business: "#f59e0b",
  enterprise: "#10b981",
};

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  active:   { bg: "#d1fae5", color: "#065f46" },
  trialing: { bg: "#dbeafe", color: "#1e40af" },
  past_due: { bg: "#fee2e2", color: "#991b1b" },
  canceled: { bg: "#f3f4f6", color: "#374151" },
  expired:  { bg: "#fef3c7", color: "#92400e" },
};

const ALL_STATUSES = ["active", "trialing", "past_due", "canceled", "expired"];
const ALL_PLANS = ["free", "pro", "business", "enterprise"];

function fmt(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("ru-RU", { day: "2-digit", month: "short", year: "numeric" });
}

export function SuperadminBillingList() {
  const { accessToken } = useAuth();
  const { t } = useLanguage();

  const sb = useCallback((key: string) => String(t(`superadmin.billing.${key}`)), [t]);
  const sc = useCallback((key: string) => String(t(`superadmin.common.${key}`)), [t]);

  const STATUS_LABELS: Record<string, string> = {
    active: sb("statusActive"),
    trialing: sb("statusTrialing"),
    past_due: sb("statusPastDue"),
    canceled: sb("statusCanceled"),
    expired: sb("statusExpired"),
  };

  const [items, setItems] = useState<AdminBillingListItemDto[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const [overrideUserId, setOverrideUserId] = useState<string | null>(null);
  const [overridePlan, setOverridePlan] = useState("pro");
  const [overrideReason, setOverrideReason] = useState("");
  const [overriding, setOverriding] = useState(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAdminBilling(accessToken, {
        limit,
        offset,
        status: statusFilter || undefined,
        plan_slug: planFilter || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setLoading(false);
    }
  }, [accessToken, offset, statusFilter, planFilter, sc]);

  useEffect(() => { void load(); }, [load]);

  async function handleOverride() {
    if (!overrideUserId) return;
    setOverriding(true);
    setOverrideError(null);
    try {
      await adminOverrideSubscription(accessToken, overrideUserId, overridePlan, overrideReason || undefined);
      setOverrideUserId(null);
      setOverrideReason("");
      await load();
    } catch (e) {
      setOverrideError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setOverriding(false);
    }
  }

  const planStats = useMemo(() => {
    const counts: Record<string, number> = {};
    items.forEach(item => {
      counts[item.plan_slug] = (counts[item.plan_slug] || 0) + 1;
    });
    return Object.entries(counts).map(([plan_slug, count]) => ({ plan_slug, count }));
  }, [items]);

  const pages = Math.ceil(total / limit);
  const page = Math.floor(offset / limit);

  return (
    <div>
      {/* Summary stats */}
      {!loading && items.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <div className={styles.cardGrid}>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("totalActive")}</p>
              <p className={styles.statValue} style={{ color: "#10b981" }}>
                {items.filter(i => i.status === "active").length}
              </p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("totalPastDue")}</p>
              <p className={styles.statValue} style={{ color: "#dc2626" }}>
                {items.filter(i => i.status === "past_due").length}
              </p>
            </div>
            <div className={styles.statCard}>
              <p className={styles.statLabel}>{sb("estimatedMrr")}</p>
              <p className={styles.statValue} style={{ color: "#10b981" }}>
                ${items.reduce((sum, i) => sum + (PLAN_PRICES[i.plan_slug] || 0), 0)}
              </p>
              <p style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)" }}>{sb("mrrNote")}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
          className={styles.filterInput}
        >
          <option value="">{sc("allStatuses")}</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s] ?? s}</option>
          ))}
        </select>
        <select
          value={planFilter}
          onChange={(e) => { setPlanFilter(e.target.value); setOffset(0); }}
          className={styles.filterInput}
        >
          <option value="">{sc("allPlans")}</option>
          {ALL_PLANS.map((p) => (
            <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)} {PLAN_PRICES[p] ? `($${PLAN_PRICES[p]}/mo)` : `(${sb("free")})`}</option>
          ))}
        </select>
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
                <th className={styles.th}>{sb("user")}</th>
                <th className={styles.th}>{sb("plan")}</th>
                <th className={styles.th}>{sc("status")}</th>
                <th className={styles.th}>{sb("periodStart")}</th>
                <th className={styles.th}>{sb("periodEnd")}</th>
                <th className={styles.th}>{sb("canceled")}</th>
                <th className={styles.th}>{sb("stripe")}</th>
                <th className={styles.th}>{sc("actions")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const sColor = STATUS_COLORS[item.status] ?? { bg: "#f3f4f6", color: "#374151" };
                return (
                  <tr key={item.user_id} className={styles.row}>
                    <td className={styles.td}>
                      <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                        {item.user_full_name || "—"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>
                        <Link href={`/superadmin/users/${item.user_id}`} style={{ color: "var(--bf-accent)" }}>
                          {item.user_email}
                        </Link>
                      </div>
                      {!item.user_is_active && (
                        <span style={{ fontSize: "0.7rem", background: "#fca5a5", color: "#7f1d1d", borderRadius: 4, padding: "1px 5px" }}>{sb("blocked")}</span>
                      )}
                    </td>
                    <td className={styles.td}>
                      <span style={{
                        fontWeight: 700,
                        fontSize: "0.8rem",
                        color: PLAN_COLORS[item.plan_slug] ?? "#374151",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}>
                        {item.plan_slug}
                      </span>
                      {(PLAN_PRICES[item.plan_slug] ?? 0) > 0 && (
                        <div style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)" }}>
                          ${PLAN_PRICES[item.plan_slug]}/mo
                        </div>
                      )}
                    </td>
                    <td className={styles.td}>
                      <span style={{
                        background: sColor.bg, color: sColor.color,
                        borderRadius: 6, padding: "2px 8px",
                        fontSize: "0.78rem", fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}>
                        {STATUS_LABELS[item.status] ?? item.status}
                      </span>
                    </td>
                    <td className={styles.td} style={{ fontSize: "0.8rem" }}>{fmt(item.current_period_start)}</td>
                    <td className={styles.td} style={{ fontSize: "0.8rem" }}>
                      <span style={item.current_period_end && new Date(item.current_period_end) < new Date() ? { color: "#dc2626", fontWeight: 600 } : {}}>
                        {fmt(item.current_period_end)}
                      </span>
                    </td>
                    <td className={styles.td} style={{ fontSize: "0.8rem" }}>{fmt(item.canceled_at)}</td>
                    <td className={styles.td} style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>
                      {item.stripe_customer_id
                        ? <span title={item.stripe_subscription_id ?? undefined}>{item.stripe_customer_id.slice(0, 14)}…</span>
                        : sb("manual")}
                    </td>
                    <td className={styles.td}>
                      <button
                        className={styles.actionBtn}
                        onClick={() => { setOverrideUserId(item.user_id); setOverridePlan(item.plan_slug); setOverrideError(null); }}
                        style={{ fontSize: "0.78rem", padding: "3px 10px" }}
                      >
                        {sb("changePlan")}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: "2rem", color: "var(--bf-text-muted)" }}>
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

      {/* Override modal */}
      {overrideUserId && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "var(--bf-surface)", borderRadius: 12, padding: "1.5rem",
            width: "min(420px, 95vw)", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}>
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>{sb("changePlanTitle")}</h3>
            <label style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.85rem" }}>{sb("newPlan")}</label>
            <select
              value={overridePlan}
              onChange={(e) => setOverridePlan(e.target.value)}
              style={{ width: "100%", marginBottom: "0.75rem", padding: "0.5rem", borderRadius: 6, border: "1px solid var(--bf-border)" }}
            >
              {ALL_PLANS.map((p) => (
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)} {PLAN_PRICES[p] ? `— $${PLAN_PRICES[p]}/mo` : `— ${sb("free")}`}</option>
              ))}
            </select>
            <label style={{ display: "block", marginBottom: "0.5rem", fontSize: "0.85rem" }}>{sb("reason")}</label>
            <input
              type="text"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder={sb("reasonPlaceholder")}
              style={{ width: "100%", marginBottom: "1rem", padding: "0.5rem", borderRadius: 6, border: "1px solid var(--bf-border)", boxSizing: "border-box" }}
            />
            {overrideError && <p style={{ color: "#dc2626", fontSize: "0.82rem", marginBottom: "0.75rem" }}>{overrideError}</p>}
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button onClick={() => setOverrideUserId(null)} style={{ padding: "0.5rem 1rem", borderRadius: 6, border: "1px solid var(--bf-border)", background: "none", cursor: "pointer" }}>
                {sc("cancel")}
              </button>
              <button
                onClick={handleOverride}
                disabled={overriding}
                style={{ padding: "0.5rem 1rem", borderRadius: 6, background: "var(--bf-accent)", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}
              >
                {overriding ? sc("saving") : sc("save")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
