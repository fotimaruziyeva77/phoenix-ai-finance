"use client";

import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import {
  type FeatureFlagDto,
  createFeatureFlag,
  deleteFeatureFlag,
  listFeatureFlags,
  updateFeatureFlag,
} from "@/lib/api/platform-admin";

import styles from "@/components/superadmin/superadmin.module.css";

const ALL_PLANS = ["free", "pro", "business", "enterprise"];

const PLAN_COLORS: Record<string, string> = {
  free: "#6b7280", pro: "#8b5cf6",
  business: "#f59e0b", enterprise: "#10b981",
};

type ModalMode = "create" | "edit";

interface FlagForm {
  key: string;
  description: string;
  is_enabled: boolean;
  target_plan: string;
  target_user_emails: string[];
}

const EMPTY_FORM: FlagForm = { key: "", description: "", is_enabled: false, target_plan: "", target_user_emails: [] };

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function SuperadminFeatureFlags() {
  const { accessToken } = useAuth();
  const { t } = useLanguage();

  const s = useCallback((key: string) => String(t(`superadmin.flags.${key}`)), [t]);
  const sc = useCallback((key: string) => String(t(`superadmin.common.${key}`)), [t]);

  const [flags, setFlags]     = useState<FeatureFlagDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  // modal
  const [modal, setModal]     = useState<ModalMode | null>(null);
  const [editId, setEditId]   = useState<string | null>(null);
  const [form, setForm]       = useState<FlagForm>(EMPTY_FORM);
  const [saving, setSaving]   = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // delete confirm
  const [deleteTarget, setDeleteTarget] = useState<FeatureFlagDto | null>(null);
  const [deleting, setDeleting]         = useState(false);
  const [deleteError, setDeleteError]   = useState<string | null>(null);

  // toggle error (replaces alert)
  const [toggleError, setToggleError] = useState<string | null>(null);

  // email targeting input
  const [emailInput, setEmailInput] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listFeatureFlags(accessToken);
      setFlags(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setLoading(false);
    }
  }, [accessToken, sc]);

  useEffect(() => { void load(); }, [load]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setEditId(null);
    setFormError(null);
    setEmailInput("");
    setEmailError(null);
    setModal("create");
  }

  function openEdit(flag: FeatureFlagDto) {
    setForm({
      key:         flag.key,
      description: flag.description ?? "",
      is_enabled:  flag.is_enabled,
      target_plan: flag.target_plan ?? "",
      target_user_emails: flag.target_user_emails ?? [],
    });
    setEditId(flag.id);
    setFormError(null);
    setEmailInput("");
    setEmailError(null);
    setModal("edit");
  }

  function addEmail() {
    const email = emailInput.trim().toLowerCase();
    if (!email) return;
    if (!isValidEmail(email)) {
      setEmailError(s("invalidEmail"));
      return;
    }
    if (form.target_user_emails.includes(email)) {
      setEmailError(null);
      setEmailInput("");
      return;
    }
    setForm((f) => ({ ...f, target_user_emails: [...f.target_user_emails, email] }));
    setEmailInput("");
    setEmailError(null);
  }

  function removeEmail(email: string) {
    setForm((f) => ({ ...f, target_user_emails: f.target_user_emails.filter((e) => e !== email) }));
  }

  async function handleSave() {
    setSaving(true);
    setFormError(null);
    try {
      if (modal === "create") {
        await createFeatureFlag(accessToken, {
          key:         form.key.trim(),
          description: form.description.trim() || null,
          is_enabled:  form.is_enabled,
          target_plan: form.target_plan || null,
          target_user_emails: form.target_user_emails.length > 0 ? form.target_user_emails : null,
        });
      } else if (editId) {
        await updateFeatureFlag(accessToken, editId, {
          is_enabled:        form.is_enabled,
          description:       form.description.trim() || null,
          target_plan:       form.target_plan || null,
          clear_target_plan: !form.target_plan,
          target_user_emails: form.target_user_emails.length > 0 ? form.target_user_emails : null,
          clear_target_users: form.target_user_emails.length === 0,
        });
      }
      setModal(null);
      await load();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteFeatureFlag(accessToken, deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : sc("error"));
    } finally {
      setDeleting(false);
    }
  }

  async function quickToggle(flag: FeatureFlagDto) {
    setToggleError(null);
    try {
      await updateFeatureFlag(accessToken, flag.id, { is_enabled: !flag.is_enabled });
      await load();
    } catch (e) {
      setToggleError(e instanceof Error ? e.message : sc("error"));
    }
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.85rem", color: "var(--bf-text-muted)" }}>
          {sc("total")}: <strong>{flags.length}</strong> {s("total")}
        </span>
        <button
          className={styles.btnPrimary}
          onClick={openCreate}
          style={{ fontSize: "0.82rem", padding: "0.4rem 1rem" }}
        >
          {s("newFlag")}
        </button>
      </div>

      {error && <p className={styles.errorBanner}>{error}</p>}
      {toggleError && <p className={styles.errorBanner}>{toggleError}</p>}

      {loading ? (
        <p style={{ color: "var(--bf-text-muted)" }}>{sc("loading")}</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>{s("key")}</th>
                <th className={styles.th}>{s("state")}</th>
                <th className={styles.th}>{s("plan")}</th>
                <th className={styles.th}>{s("targetUsers")}</th>
                <th className={styles.th}>{s("description")}</th>
                <th className={styles.th}>{s("updated")}</th>
                <th className={styles.th}>{sc("actions")}</th>
              </tr>
            </thead>
            <tbody>
              {flags.map((flag) => (
                <tr key={flag.id} className={styles.row}>
                  <td className={styles.td}>
                    <code style={{ fontSize: "0.82rem", fontWeight: 700 }}>{flag.key}</code>
                  </td>
                  <td className={styles.td}>
                    <button
                      onClick={() => quickToggle(flag)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        background: flag.is_enabled ? "#d1fae5" : "#f3f4f6",
                        color: flag.is_enabled ? "#065f46" : "#374151",
                        border: "none",
                        borderRadius: 20,
                        padding: "3px 10px",
                        fontSize: "0.75rem",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                      title={s("toggleTitle")}
                    >
                      <span style={{
                        width: 8, height: 8, borderRadius: "50%",
                        background: flag.is_enabled ? "#10b981" : "#9ca3af",
                        display: "inline-block",
                      }} />
                      {flag.is_enabled ? s("enabled") : s("disabled")}
                    </button>
                  </td>
                  <td className={styles.td}>
                    {flag.target_plan ? (
                      <span style={{
                        background: "#f3f4f6",
                        color: PLAN_COLORS[flag.target_plan] ?? "#374151",
                        borderRadius: 5, padding: "2px 8px",
                        fontSize: "0.75rem", fontWeight: 700,
                        textTransform: "uppercase",
                      }}>
                        {flag.target_plan}
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>Global</span>
                    )}
                  </td>
                  <td className={styles.td}>
                    {flag.target_user_emails && flag.target_user_emails.length > 0 ? (
                      <span
                        style={{
                          background: "#eff6ff",
                          color: "#1d4ed8",
                          borderRadius: 5,
                          padding: "2px 8px",
                          fontSize: "0.75rem",
                          fontWeight: 700,
                        }}
                        title={flag.target_user_emails.join(", ")}
                      >
                        {flag.target_user_emails.length} {s("usersTargeted")}
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>
                        {s("noUserTarget")}
                      </span>
                    )}
                  </td>
                  <td className={styles.td} style={{ fontSize: "0.8rem", color: "var(--bf-text-muted)", maxWidth: 200 }}>
                    {flag.description ?? "—"}
                  </td>
                  <td className={styles.td} style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)", whiteSpace: "nowrap" }}>
                    {new Date(flag.updated_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "short", year: "numeric" })}
                  </td>
                  <td className={styles.td}>
                    <div style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        className={styles.actionBtn}
                        onClick={() => openEdit(flag)}
                        style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                      >
                        {sc("edit")}
                      </button>
                      <button
                        onClick={() => { setDeleteTarget(flag); setDeleteError(null); }}
                        style={{
                          fontSize: "0.75rem", padding: "2px 8px",
                          background: "color-mix(in srgb, #dc2626 12%, transparent)",
                          border: "1px solid color-mix(in srgb, #dc2626 30%, transparent)",
                          borderRadius: 6, cursor: "pointer", color: "var(--bf-text)",
                        }}
                      >
                        {sc("delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {flags.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "2rem", color: "var(--bf-text-muted)" }}>
                    {s("emptyState")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit modal */}
      {modal && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "var(--bf-surface)", borderRadius: 12, padding: "1.5rem",
            width: "min(460px, 95vw)", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}>
            <h3 style={{ margin: "0 0 1rem", fontSize: "1rem" }}>
              {modal === "create" ? s("createTitle") : s("editTitle")}
            </h3>

            {modal === "create" && (
              <div style={{ marginBottom: "0.75rem" }}>
                <label className={styles.modalFieldLabel}>{s("keyLabel")}</label>
                <input
                  type="text"
                  value={form.key}
                  onChange={(e) => setForm((f) => ({ ...f, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_") }))}
                  placeholder={s("keyPlaceholder")}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid var(--bf-border)", boxSizing: "border-box", fontFamily: "monospace" }}
                />
                <p style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)", margin: "2px 0 0" }}>{s("keyHelp")}</p>
              </div>
            )}

            <div style={{ marginBottom: "0.75rem" }}>
              <label className={styles.modalFieldLabel}>{s("descLabel")}</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder={s("descPlaceholder")}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid var(--bf-border)", boxSizing: "border-box" }}
              />
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <label className={styles.modalFieldLabel}>{s("targetPlan")}</label>
              <select
                value={form.target_plan}
                onChange={(e) => setForm((f) => ({ ...f, target_plan: e.target.value }))}
                style={{ width: "100%", padding: "0.5rem", borderRadius: 6, border: "1px solid var(--bf-border)" }}
              >
                <option value="">{s("globalAllPlans")}</option>
                {ALL_PLANS.map((p) => (
                  <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                ))}
              </select>
            </div>

            {/* Target Users */}
            <div style={{ marginBottom: "0.75rem" }}>
              <label className={styles.modalFieldLabel}>{s("targetUsers")}</label>
              <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.3rem" }}>
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => { setEmailInput(e.target.value); setEmailError(null); }}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addEmail(); } }}
                  placeholder={s("emailPlaceholder")}
                  style={{
                    flex: 1, padding: "0.5rem", borderRadius: 6,
                    border: emailError ? "1px solid #dc2626" : "1px solid var(--bf-border)",
                    boxSizing: "border-box",
                  }}
                />
                <button
                  type="button"
                  onClick={addEmail}
                  style={{
                    padding: "0.5rem 0.75rem", borderRadius: 6,
                    background: "var(--bf-accent)", color: "#fff",
                    border: "none", cursor: "pointer", fontWeight: 600,
                    fontSize: "0.82rem", whiteSpace: "nowrap",
                  }}
                >
                  {s("addEmail")}
                </button>
              </div>
              {emailError && (
                <p style={{ fontSize: "0.72rem", color: "#dc2626", margin: "2px 0 0" }}>{emailError}</p>
              )}
              <p style={{ fontSize: "0.72rem", color: "var(--bf-text-muted)", margin: "2px 0 0" }}>
                {s("targetUsersHelp")}
              </p>
              {form.target_user_emails.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.4rem" }}>
                  {form.target_user_emails.map((email) => (
                    <span
                      key={email}
                      style={{
                        display: "inline-flex", alignItems: "center", gap: "0.3rem",
                        background: "#eff6ff", color: "#1d4ed8",
                        borderRadius: 12, padding: "2px 8px 2px 10px",
                        fontSize: "0.75rem", fontWeight: 500,
                      }}
                    >
                      {email}
                      <button
                        type="button"
                        onClick={() => removeEmail(email)}
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "#1d4ed8", fontWeight: 700, fontSize: "0.85rem",
                          padding: "0 2px", lineHeight: 1,
                        }}
                        title="Remove"
                      >
                        x
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer", marginBottom: "1rem" }}>
              <input
                type="checkbox"
                checked={form.is_enabled}
                onChange={(e) => setForm((f) => ({ ...f, is_enabled: e.target.checked }))}
                style={{ width: 16, height: 16 }}
              />
              {s("enableOnCreate")}
            </label>

            {formError && <p style={{ color: "#dc2626", fontSize: "0.82rem", marginBottom: "0.75rem" }}>{formError}</p>}

            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button
                onClick={() => setModal(null)}
                style={{ padding: "0.5rem 1rem", borderRadius: 6, border: "1px solid var(--bf-border)", background: "none", cursor: "pointer" }}
              >
                {sc("cancel")}
              </button>
              <button
                onClick={handleSave}
                disabled={saving || (modal === "create" && !form.key.trim())}
                style={{ padding: "0.5rem 1rem", borderRadius: 6, background: "var(--bf-accent)", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}
              >
                {saving ? sc("saving") : sc("save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {deleteTarget && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: "var(--bf-surface)", borderRadius: 12, padding: "1.5rem",
            width: "min(380px, 95vw)", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
          }}>
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>{s("deleteTitle")}</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--bf-text-muted)", margin: "0 0 0.5rem" }}>
              <code style={{ fontWeight: 700 }}>{deleteTarget.key}</code> {s("deleteConfirm")}
            </p>
            <p style={{ fontSize: "0.82rem", color: "var(--bf-text-muted)", margin: "0 0 1rem" }}>
              {s("deleteWarn")}
            </p>
            {deleteError && <p style={{ color: "#dc2626", fontSize: "0.82rem", marginBottom: "0.75rem" }}>{deleteError}</p>}
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button
                onClick={() => setDeleteTarget(null)}
                style={{ padding: "0.5rem 1rem", borderRadius: 6, border: "1px solid var(--bf-border)", background: "none", cursor: "pointer" }}
              >
                {sc("cancel")}
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                style={{ padding: "0.5rem 1rem", borderRadius: 6, background: "#dc2626", color: "#fff", border: "none", cursor: "pointer", fontWeight: 600 }}
              >
                {deleting ? sc("deleting") : s("yesDelete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
