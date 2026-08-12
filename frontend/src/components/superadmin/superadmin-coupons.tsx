"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  listCoupons,
  createCoupon,
  updateCoupon,
  deleteCoupon,
  type CouponDto,
} from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

const DISCOUNT_TYPE_LABEL: Record<string, string> = {
  percent: "%",
  usd: "$",
};

export function SuperadminCoupons() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const sk = (key: string) => String(t(`superadmin.coupons.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const [items, setItems] = useState<CouponDto[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newType, setNewType] = useState<"percent" | "usd">("percent");
  const [newValue, setNewValue] = useState("");
  const [newTargetPlan, setNewTargetPlan] = useState("");
  const [newMaxUses, setNewMaxUses] = useState("");
  const [newExpiresAt, setNewExpiresAt] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit modal
  const [editCoupon, setEditCoupon] = useState<CouponDto | null>(null);
  const [editActive, setEditActive] = useState(true);
  const [editMaxUses, setEditMaxUses] = useState("");
  const [editExpiresAt, setEditExpiresAt] = useState("");
  const [editClearExpires, setEditClearExpires] = useState(false);
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<CouponDto | null>(null);
  const [deleting, setDeleting] = useState(false);

  const analytics = useMemo(() => {
    const active = items.filter(c => c.is_active).length;
    const expired = items.filter(c => c.expires_at && new Date(c.expires_at) < new Date()).length;
    const totalRedemptions = items.reduce((sum, c) => sum + c.used_count, 0);
    const avgDiscount = items.length > 0
      ? items.reduce((sum, c) => sum + parseFloat(c.discount_value), 0) / items.length
      : 0;
    const maxedOut = items.filter(c => c.max_uses != null && c.used_count >= c.max_uses).length;
    return { active, expired, totalRedemptions, avgDiscount, maxedOut };
  }, [items]);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await listCoupons(token);
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError(sk("loadError"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate() {
    if (!token || !newCode || !newValue) return;
    setCreating(true);
    setError("");
    try {
      const created = await createCoupon(token, {
        code: newCode.toUpperCase(),
        discount_type: newType,
        discount_value: newValue,
        target_plan: newTargetPlan || null,
        max_uses: newMaxUses ? parseInt(newMaxUses) : null,
        expires_at: newExpiresAt || null,
      });
      setItems(prev => [created, ...prev]);
      setTotal(t => t + 1);
      setShowCreate(false);
      resetCreate();
      setSuccess(`${sk("couponCreated")}: ${created.code}`);
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : sk("loadError");
      setError(msg.includes("409") ? sk("codeExists") : msg);
    } finally {
      setCreating(false);
    }
  }

  function resetCreate() {
    setNewCode(""); setNewType("percent"); setNewValue("");
    setNewTargetPlan(""); setNewMaxUses(""); setNewExpiresAt("");
  }

  function openEdit(c: CouponDto) {
    setEditCoupon(c);
    setEditActive(c.is_active);
    setEditMaxUses(c.max_uses != null ? String(c.max_uses) : "");
    setEditExpiresAt(c.expires_at ? c.expires_at.slice(0, 16) : "");
    setEditClearExpires(false);
  }

  async function handleEdit() {
    if (!editCoupon || !token) return;
    setSaving(true);
    try {
      const updated = await updateCoupon(token, editCoupon.id, {
        is_active: editActive,
        max_uses: editMaxUses ? parseInt(editMaxUses) : null,
        expires_at: editClearExpires ? null : (editExpiresAt || null),
        clear_expires: editClearExpires,
      });
      setItems(prev => prev.map(c => c.id === updated.id ? updated : c));
      setEditCoupon(null);
    } catch {
      setError(sk("loadError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget || !token) return;
    setDeleting(true);
    try {
      await deleteCoupon(token, deleteTarget.id);
      setItems(prev => prev.filter(c => c.id !== deleteTarget.id));
      setTotal(t => t - 1);
      setDeleteTarget(null);
    } catch {
      setError(sk("loadError"));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}
      {success && <p className={styles.successBanner}>{success}</p>}

      {!loading && items.length > 0 && (
        <div className={styles.cardGrid} style={{ marginBottom: "1rem" }}>
          <div className={styles.statCard}>
            <p className={styles.statLabel}>{sk("analyticsActive")}</p>
            <p className={styles.statValue} style={{ color: "#10b981" }}>{analytics.active}</p>
          </div>
          <div className={styles.statCard}>
            <p className={styles.statLabel}>{sk("analyticsRedemptions")}</p>
            <p className={styles.statValue}>{analytics.totalRedemptions}</p>
          </div>
          <div className={styles.statCard}>
            <p className={styles.statLabel}>{sk("analyticsExpired")}</p>
            <p className={styles.statValue} style={{ color: analytics.expired > 0 ? "#dc2626" : undefined }}>{analytics.expired}</p>
          </div>
          <div className={styles.statCard}>
            <p className={styles.statLabel}>{sk("analyticsMaxedOut")}</p>
            <p className={styles.statValue} style={{ color: "#f59e0b" }}>{analytics.maxedOut}</p>
          </div>
          <div className={styles.statCard}>
            <p className={styles.statLabel}>{sk("analyticsAvgDiscount")}</p>
            <p className={styles.statValue}>{analytics.avgDiscount.toFixed(1)}</p>
          </div>
        </div>
      )}

      <div className={styles.toolbar}>
        <button className={styles.btnPrimary} onClick={() => setShowCreate(true)}>{sk("newCoupon")}</button>
        <span className={styles.toolbarMeta}>{total} {sk("couponsCount")}</span>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>{sk("code")}</th>
              <th className={styles.th}>{sk("discount")}</th>
              <th className={styles.th}>{sk("plan")}</th>
              <th className={styles.th}>{sk("uses")}</th>
              <th className={styles.th}>{sk("expires")}</th>
              <th className={styles.th}>{sk("status")}</th>
              <th className={styles.th}>{sk("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className={styles.td} colSpan={7} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sc("loading")}</td></tr>
            ) : items.length === 0 ? (
              <tr><td className={styles.td} colSpan={7} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sk("noCoupons")}</td></tr>
            ) : items.map(c => (
              <tr key={c.id} className={styles.row}>
                <td className={styles.td} style={{ fontWeight: 700, fontFamily: "monospace", letterSpacing: "0.04em" }}>{c.code}</td>
                <td className={styles.td}>
                  {c.discount_type === "percent" ? `${c.discount_value}%` : `$${c.discount_value}`}
                  <span className={`${styles.badge} ${styles.badgeMuted}`} style={{ marginLeft: "0.35rem" }}>{DISCOUNT_TYPE_LABEL[c.discount_type]}</span>
                </td>
                <td className={styles.td}>{c.target_plan ? <span className={styles.badgeOk}>{c.target_plan}</span> : <span className={styles.badgeMuted}>{sk("allPlans")}</span>}</td>
                <td className={styles.td}>{c.used_count}{c.max_uses != null ? ` / ${c.max_uses}` : ""}</td>
                <td className={styles.td}>{c.expires_at ? new Date(c.expires_at).toLocaleDateString() : "—"}</td>
                <td className={styles.td}>
                  <span className={c.is_active ? styles.badgeOk : styles.badgeBad}>{c.is_active ? sk("active") : sk("inactive")}</span>
                </td>
                <td className={styles.td}>
                  <div style={{ display: "flex", gap: "0.35rem" }}>
                    <button className={styles.actionBtn} onClick={() => openEdit(c)}>{sk("edit")}</button>
                    <button className={`${styles.actionBtn} ${styles.btnDanger}`} style={{ background: "color-mix(in srgb, #c0392b 14%, transparent)", border: "1px solid color-mix(in srgb, #c0392b 40%, transparent)" }} onClick={() => setDeleteTarget(c)}>{sk("delete")}</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className={styles.modalOverlay} onClick={() => setShowCreate(false)}>
          <div className={styles.modal} style={{ width: "min(30rem, 100%)" }} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{sk("createTitle")}</h3>

            <label className={styles.modalFieldLabel}>{sk("codeLabel")}</label>
            <input
              className={styles.filterInput}
              style={{ width: "100%", marginBottom: "0.65rem" }}
              placeholder="LAUNCH50"
              value={newCode}
              onChange={e => setNewCode(e.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, ""))}
            />

            <div style={{ display: "flex", gap: "0.65rem", marginBottom: "0.65rem" }}>
              <div style={{ flex: 1 }}>
                <label className={styles.modalFieldLabel}>{sk("typeLabel")}</label>
                <select className={styles.filterInput} style={{ width: "100%" }} value={newType} onChange={e => setNewType(e.target.value as "percent" | "usd")}>
                  <option value="percent">{sk("percentType")}</option>
                  <option value="usd">{sk("usdType")}</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label className={styles.modalFieldLabel}>{sk("valueLabel")}</label>
                <input className={styles.filterInput} style={{ width: "100%" }} type="number" min="0" placeholder="e.g. 20" value={newValue} onChange={e => setNewValue(e.target.value)} />
              </div>
            </div>

            <label className={styles.modalFieldLabel}>{sk("targetPlan")}</label>
            <input className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} placeholder="pro / business / enterprise" value={newTargetPlan} onChange={e => setNewTargetPlan(e.target.value)} />

            <div style={{ display: "flex", gap: "0.65rem", marginBottom: "0.85rem" }}>
              <div style={{ flex: 1 }}>
                <label className={styles.modalFieldLabel}>{sk("maxUses")}</label>
                <input className={styles.filterInput} style={{ width: "100%" }} type="number" min="1" placeholder="unlimited" value={newMaxUses} onChange={e => setNewMaxUses(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label className={styles.modalFieldLabel}>{sk("expiresAt")}</label>
                <input className={styles.filterInput} style={{ width: "100%" }} type="datetime-local" value={newExpiresAt} onChange={e => setNewExpiresAt(e.target.value)} />
              </div>
            </div>

            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => { setShowCreate(false); resetCreate(); }}>{sk("cancel")}</button>
              <button className={styles.btnPrimary} disabled={creating || !newCode || !newValue} onClick={handleCreate}>
                {creating ? sk("creating") : sk("create")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editCoupon && (
        <div className={styles.modalOverlay} onClick={() => setEditCoupon(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{sk("editTitle")}: {editCoupon.code}</h3>

            <label className={styles.modalFieldLabel}>{sk("activeLabel")}</label>
            <select className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} value={editActive ? "true" : "false"} onChange={e => setEditActive(e.target.value === "true")}>
              <option value="true">{sk("activeLabel")}</option>
              <option value="false">{sk("inactiveLabel")}</option>
            </select>

            <label className={styles.modalFieldLabel}>{sk("maxUses")}</label>
            <input className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} type="number" min="1" placeholder="unlimited" value={editMaxUses} onChange={e => setEditMaxUses(e.target.value)} />

            <label className={styles.modalFieldLabel}>{sk("expiresAt")}</label>
            <input className={styles.filterInput} style={{ width: "100%", marginBottom: "0.35rem" }} type="datetime-local" value={editExpiresAt} disabled={editClearExpires} onChange={e => setEditExpiresAt(e.target.value)} />
            <label style={{ fontSize: "0.8rem", color: "var(--bf-text-muted)", display: "flex", alignItems: "center", gap: "0.35rem", marginBottom: "0.85rem", cursor: "pointer" }}>
              <input type="checkbox" checked={editClearExpires} onChange={e => setEditClearExpires(e.target.checked)} />
              {sk("clearExpiry")}
            </label>

            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setEditCoupon(null)}>{sk("cancel")}</button>
              <button className={styles.btnPrimary} disabled={saving} onClick={handleEdit}>
                {saving ? sk("saving") : sk("save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteTarget && (
        <div className={styles.modalOverlay} onClick={() => setDeleteTarget(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{sk("deleteTitle")}</h3>
            <p className={styles.modalHint}>{sk("deleteConfirm")} <strong>{deleteTarget.code}</strong></p>
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setDeleteTarget(null)}>{sk("cancel")}</button>
              <button className={styles.btnDanger} disabled={deleting} onClick={handleDelete}>
                {deleting ? sk("deleting") : sk("delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
