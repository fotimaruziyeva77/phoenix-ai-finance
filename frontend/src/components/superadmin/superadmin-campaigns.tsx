"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/language-context";
import {
  listCampaigns,
  createCampaign,
  updateCampaign,
  sendCampaign,
  deleteCampaign,
  type CampaignDto,
  type CampaignListResponseDto,
} from "@/lib/api/platform-admin";
import styles from "./superadmin.module.css";

const STATUS_CLASS: Record<string, string> = {
  draft: "badgeMuted",
  sending: "badgeWarn",
  sent: "badgeOk",
  failed: "badgeBad",
};

const PAGE_SIZE = 50;

type EmailTemplate = {
  id: string;
  nameKey: string;
  descKey: string;
  html: string;
};

const EMAIL_TEMPLATES: EmailTemplate[] = [
  {
    id: "welcome",
    nameKey: "tplWelcome",
    descKey: "tplWelcomeDesc",
    html: `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
  <div style="text-align: center; margin-bottom: 24px;">
    <h1 style="color: #1a1a2e; font-size: 24px; margin: 0;">Welcome to BotForge! 🚀</h1>
  </div>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">Hi {{name}},</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">We're thrilled to have you on board. Your AI chatbot journey starts here.</p>
  <div style="text-align: center; margin: 32px 0;">
    <a href="https://botforge.uz/dashboard" style="background: #6366f1; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Get Started</a>
  </div>
  <p style="color: #6b7280; font-size: 14px; line-height: 1.5;">If you have any questions, just reply to this email.</p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
  <p style="color: #9ca3af; font-size: 12px; text-align: center;">BotForge AI · Tashkent, Uzbekistan</p>
</div>`,
  },
  {
    id: "announcement",
    nameKey: "tplAnnouncement",
    descKey: "tplAnnouncementDesc",
    html: `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
  <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 12px; padding: 32px; margin-bottom: 24px; text-align: center;">
    <h1 style="color: #ffffff; font-size: 22px; margin: 0;">📢 Important Update</h1>
  </div>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">Hi {{name}},</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">We have exciting news to share with you!</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">[Your announcement details here]</p>
  <div style="text-align: center; margin: 32px 0;">
    <a href="https://botforge.uz" style="background: #6366f1; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">Learn More</a>
  </div>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
  <p style="color: #9ca3af; font-size: 12px; text-align: center;">BotForge AI · Tashkent, Uzbekistan</p>
</div>`,
  },
  {
    id: "promotion",
    nameKey: "tplPromotion",
    descKey: "tplPromotionDesc",
    html: `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
  <div style="background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%); border-radius: 12px; padding: 32px; margin-bottom: 24px; text-align: center;">
    <h1 style="color: #ffffff; font-size: 22px; margin: 0;">🎉 Special Offer!</h1>
    <p style="color: #ffffff; font-size: 36px; font-weight: 800; margin: 12px 0 0;">20% OFF</p>
  </div>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">Hi {{name}},</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">For a limited time, upgrade your plan and save 20%!</p>
  <div style="background: #fef3c7; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <p style="color: #92400e; font-size: 14px; margin: 0; font-weight: 600;">Use code: <span style="font-family: monospace; font-size: 18px;">UPGRADE20</span></p>
  </div>
  <div style="text-align: center; margin: 32px 0;">
    <a href="https://botforge.uz/pricing" style="background: #f59e0b; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">Upgrade Now</a>
  </div>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
  <p style="color: #9ca3af; font-size: 12px; text-align: center;">BotForge AI · Tashkent, Uzbekistan</p>
</div>`,
  },
  {
    id: "reengagement",
    nameKey: "tplReengagement",
    descKey: "tplReengagementDesc",
    html: `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px 24px; background: #ffffff;">
  <div style="text-align: center; margin-bottom: 24px;">
    <h1 style="color: #1a1a2e; font-size: 24px; margin: 0;">We miss you! 👋</h1>
  </div>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">Hi {{name}},</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">It's been a while since we last saw you. Your chatbot is waiting for you!</p>
  <p style="color: #374151; font-size: 16px; line-height: 1.6;">Here's what you can do today:</p>
  <ul style="color: #374151; font-size: 15px; line-height: 1.8; padding-left: 20px;">
    <li>Train your bot with new knowledge</li>
    <li>Check your conversation analytics</li>
    <li>Try our latest AI features</li>
  </ul>
  <div style="text-align: center; margin: 32px 0;">
    <a href="https://botforge.uz/dashboard" style="background: #6366f1; color: #fff; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">Come Back</a>
  </div>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;" />
  <p style="color: #9ca3af; font-size: 12px; text-align: center;">BotForge AI · Tashkent, Uzbekistan</p>
</div>`,
  },
];

const TEMPLATE_ICONS: Record<string, string> = {
  blank: "📄",
  welcome: "🚀",
  announcement: "📢",
  promotion: "🎉",
  reengagement: "👋",
};

export function SuperadminCampaigns() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();
  const scm = (key: string) => String(t(`superadmin.campaigns.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const SEGMENT_LABELS: Record<string, string> = {
    all_users: scm("segmentAllUsers"),
    past_due: scm("segmentPastDue"),
    free_plan: scm("segmentFreePlan"),
    paid_users: scm("segmentPaidUsers"),
    inactive_7d: scm("segmentInactive7d"),
  };

  const [items, setItems] = useState<CampaignDto[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [newSubject, setNewSubject] = useState("");
  const [newSegment, setNewSegment] = useState("all_users");
  const [newBodyHtml, setNewBodyHtml] = useState("");
  const [creating, setCreating] = useState(false);
  const [selectedCreateTpl, setSelectedCreateTpl] = useState<string>("blank");

  // Edit modal
  const [editTarget, setEditTarget] = useState<CampaignDto | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBodyHtml, setEditBodyHtml] = useState("");
  const [editSegment, setEditSegment] = useState("");
  const [editing, setEditing] = useState(false);
  const [selectedEditTpl, setSelectedEditTpl] = useState<string>("blank");

  // Preview modal
  const [previewCampaign, setPreviewCampaign] = useState<CampaignDto | null>(null);

  // Send confirm
  const [sendTarget, setSendTarget] = useState<CampaignDto | null>(null);
  const [sending, setSending] = useState(false);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<CampaignDto | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function load(off = offset) {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res: CampaignListResponseDto = await listCampaigns(token, { limit: PAGE_SIZE, offset: off });
      setItems(res.items);
      setTotal(res.total);
    } catch {
      setError(scm("loadError"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(0); setOffset(0); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate() {
    if (!token || !newSubject || !newBodyHtml) return;
    setCreating(true);
    setError("");
    try {
      const created = await createCampaign(token, {
        subject: newSubject,
        body_html: newBodyHtml,
        target_segment: newSegment,
      });
      setItems(prev => [created, ...prev]);
      setTotal(t => t + 1);
      setShowCreate(false);
      setNewSubject(""); setNewBodyHtml(""); setNewSegment("all_users"); setSelectedCreateTpl("blank");
      setSuccess(`${scm("campaignCreated")} "${created.subject}" (${created.estimated_recipients ?? "?"} ${scm("recipients")}).`);
      setTimeout(() => setSuccess(""), 4000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : scm("createError"));
    } finally {
      setCreating(false);
    }
  }

  function openEdit(c: CampaignDto) {
    setEditTarget(c);
    setEditSubject(c.subject);
    setEditBodyHtml(c.body_html);
    setEditSegment(c.target_segment);
  }

  async function handleEdit() {
    if (!editTarget || !token) return;
    setEditing(true);
    setError("");
    try {
      const updated = await updateCampaign(token, editTarget.id, {
        subject: editSubject,
        body_html: editBodyHtml,
        target_segment: editSegment,
      });
      setItems(prev => prev.map(c => c.id === updated.id ? updated : c));
      setEditTarget(null);
      setSuccess(scm("campaignUpdated"));
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : scm("updateError"));
    } finally {
      setEditing(false);
    }
  }

  async function handleSend() {
    if (!sendTarget || !token) return;
    setSending(true);
    try {
      const updated = await sendCampaign(token, sendTarget.id);
      setItems(prev => prev.map(c => c.id === updated.id ? updated : c));
      setSendTarget(null);
      setSuccess(`${scm("campaignSending")} ~${updated.estimated_recipients ?? "?"} ${scm("recipients")}.`);
      setTimeout(() => setSuccess(""), 5000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : scm("sendError"));
    } finally {
      setSending(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget || !token) return;
    setDeleting(true);
    try {
      await deleteCampaign(token, deleteTarget.id);
      setItems(prev => prev.filter(c => c.id !== deleteTarget.id));
      setTotal(t => t - 1);
      setDeleteTarget(null);
    } catch {
      setError(scm("deleteError"));
    } finally {
      setDeleting(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className={styles.stack}>
      {error && <p className={styles.errorBanner}>{error}</p>}
      {success && <p className={styles.successBanner}>{success}</p>}

      <div className={styles.toolbar}>
        <button className={styles.btnPrimary} onClick={() => setShowCreate(true)}>{scm("newCampaign")}</button>
        <span className={styles.toolbarMeta}>{total} {scm("campaignsCount")}</span>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>{scm("subject")}</th>
              <th className={styles.th}>{scm("segment")}</th>
              <th className={styles.th}>{scm("status")}</th>
              <th className={styles.th}>{scm("sentFailed")}</th>
              <th className={styles.th}>{scm("sentAt")}</th>
              <th className={styles.th}>{scm("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{sc("loading")}</td></tr>
            ) : items.length === 0 ? (
              <tr><td className={styles.td} colSpan={6} style={{ textAlign: "center", color: "var(--bf-text-muted)" }}>{scm("noCampaigns")}</td></tr>
            ) : items.map(c => (
              <tr key={c.id} className={styles.row}>
                <td className={styles.td} style={{ fontWeight: 600 }}>{c.subject}</td>
                <td className={styles.td}><span className={styles.badgeOk}>{SEGMENT_LABELS[c.target_segment] ?? c.target_segment}</span></td>
                <td className={styles.td}>
                  <span className={styles[STATUS_CLASS[c.status] ?? "badge"] as string}>
                    {c.status}
                  </span>
                  {c.estimated_recipients != null && (
                    <span className={styles.cellSub}>{c.estimated_recipients} {scm("recipients")}</span>
                  )}
                </td>
                <td className={styles.td}>
                  <span style={{ color: "var(--bf-accent-soft)" }}>{c.sent_count}</span>
                  {c.failed_count > 0 && <span style={{ color: "#c0392b", marginLeft: "0.35rem" }}>/ {c.failed_count} {scm("failedCount")}</span>}
                </td>
                <td className={styles.td}>{c.sent_at ? new Date(c.sent_at).toLocaleString() : "—"}</td>
                <td className={styles.td}>
                  <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                    <button className={styles.actionBtn} onClick={() => setPreviewCampaign(c)}>{scm("preview")}</button>
                    {(c.status === "draft" || c.status === "failed") && (
                      <>
                        <button className={styles.actionBtn} onClick={() => openEdit(c)}>{scm("edit")}</button>
                        <button className={styles.btnPrimary} style={{ fontSize: "0.78rem", padding: "3px 10px" }} onClick={() => setSendTarget(c)}>{scm("send")}</button>
                        <button className={styles.btnDanger} style={{ fontSize: "0.78rem", padding: "3px 10px" }} onClick={() => setDeleteTarget(c)}>{scm("delete")}</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className={styles.toolbar}>
          <button className={styles.pageBtn} disabled={offset === 0} onClick={() => { const o = Math.max(0, offset - PAGE_SIZE); setOffset(o); void load(o); }}>{`← ${scm("prevPage")}`}</button>
          <span style={{ fontSize: "0.8125rem", color: "var(--bf-text-muted)" }}>{scm("pageOf")} {currentPage} / {totalPages}</span>
          <button className={styles.pageBtn} disabled={offset + PAGE_SIZE >= total} onClick={() => { const o = offset + PAGE_SIZE; setOffset(o); void load(o); }}>{`${scm("nextPage")} →`}</button>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className={styles.modalOverlay} onClick={() => setShowCreate(false)}>
          <div className={styles.modal} style={{ width: "min(36rem, 100%)" }} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{scm("newTitle")}</h3>
            <label className={styles.modalFieldLabel}>{scm("subjectLabel")}</label>
            <input className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} value={newSubject} onChange={e => setNewSubject(e.target.value)} placeholder="Subject line…" />
            <label className={styles.modalFieldLabel}>{scm("targetSegment")}</label>
            <select className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} value={newSegment} onChange={e => setNewSegment(e.target.value)}>
              {Object.entries(SEGMENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className={styles.modalFieldLabel}>{scm("templateLabel")}</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.65rem" }}>
              {/* Blank option */}
              <div
                onClick={() => { setSelectedCreateTpl("blank"); setNewBodyHtml(""); }}
                style={{
                  border: selectedCreateTpl === "blank" ? "2px solid var(--bf-accent)" : "1px solid var(--bf-border)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                  cursor: "pointer",
                  background: selectedCreateTpl === "blank" ? "rgba(99,102,241,0.06)" : "transparent",
                  transition: "border-color 0.15s, background 0.15s",
                }}
              >
                <div style={{ fontSize: "1.1rem", marginBottom: "2px" }}>{TEMPLATE_ICONS.blank}</div>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--bf-text)" }}>{scm("tplBlank")}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>{scm("tplBlankDesc")}</div>
              </div>
              {/* Template options */}
              {EMAIL_TEMPLATES.map(tpl => (
                <div
                  key={tpl.id}
                  onClick={() => { setSelectedCreateTpl(tpl.id); setNewBodyHtml(tpl.html); }}
                  style={{
                    border: selectedCreateTpl === tpl.id ? "2px solid var(--bf-accent)" : "1px solid var(--bf-border)",
                    borderRadius: "8px",
                    padding: "10px 12px",
                    cursor: "pointer",
                    background: selectedCreateTpl === tpl.id ? "rgba(99,102,241,0.06)" : "transparent",
                    transition: "border-color 0.15s, background 0.15s",
                  }}
                >
                  <div style={{ fontSize: "1.1rem", marginBottom: "2px" }}>{TEMPLATE_ICONS[tpl.id] ?? "📄"}</div>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--bf-text)" }}>{scm(tpl.nameKey)}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>{scm(tpl.descKey)}</div>
                </div>
              ))}
            </div>
            <label className={styles.modalFieldLabel}>{scm("bodyLabel")}</label>
            <textarea className={styles.textarea} style={{ minHeight: "8rem" }} placeholder={`<p>Hi {{name}},</p>\n<p>Your message here…</p>`} value={newBodyHtml} onChange={e => setNewBodyHtml(e.target.value)} />
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setShowCreate(false)}>{scm("cancel")}</button>
              <button className={styles.btnPrimary} disabled={creating || !newSubject || !newBodyHtml} onClick={handleCreate}>
                {creating ? scm("creating") : scm("createDraft")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editTarget && (
        <div className={styles.modalOverlay} onClick={() => setEditTarget(null)}>
          <div className={styles.modal} style={{ width: "min(36rem, 100%)" }} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{scm("editTitle")}</h3>
            <label className={styles.modalFieldLabel}>{scm("subjectLabel")}</label>
            <input className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} value={editSubject} onChange={e => setEditSubject(e.target.value)} />
            <label className={styles.modalFieldLabel}>{scm("targetSegment")}</label>
            <select className={styles.filterInput} style={{ width: "100%", marginBottom: "0.65rem" }} value={editSegment} onChange={e => setEditSegment(e.target.value)}>
              {Object.entries(SEGMENT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className={styles.modalFieldLabel}>{scm("templateLabel")}</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.65rem" }}>
              {/* Blank option */}
              <div
                onClick={() => { setSelectedEditTpl("blank"); setEditBodyHtml(""); }}
                style={{
                  border: selectedEditTpl === "blank" ? "2px solid var(--bf-accent)" : "1px solid var(--bf-border)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                  cursor: "pointer",
                  background: selectedEditTpl === "blank" ? "rgba(99,102,241,0.06)" : "transparent",
                  transition: "border-color 0.15s, background 0.15s",
                }}
              >
                <div style={{ fontSize: "1.1rem", marginBottom: "2px" }}>{TEMPLATE_ICONS.blank}</div>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--bf-text)" }}>{scm("tplBlank")}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>{scm("tplBlankDesc")}</div>
              </div>
              {/* Template options */}
              {EMAIL_TEMPLATES.map(tpl => (
                <div
                  key={tpl.id}
                  onClick={() => { setSelectedEditTpl(tpl.id); setEditBodyHtml(tpl.html); }}
                  style={{
                    border: selectedEditTpl === tpl.id ? "2px solid var(--bf-accent)" : "1px solid var(--bf-border)",
                    borderRadius: "8px",
                    padding: "10px 12px",
                    cursor: "pointer",
                    background: selectedEditTpl === tpl.id ? "rgba(99,102,241,0.06)" : "transparent",
                    transition: "border-color 0.15s, background 0.15s",
                  }}
                >
                  <div style={{ fontSize: "1.1rem", marginBottom: "2px" }}>{TEMPLATE_ICONS[tpl.id] ?? "📄"}</div>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--bf-text)" }}>{scm(tpl.nameKey)}</div>
                  <div style={{ fontSize: "0.75rem", color: "var(--bf-text-muted)" }}>{scm(tpl.descKey)}</div>
                </div>
              ))}
            </div>
            <label className={styles.modalFieldLabel}>{scm("bodyHtml")}</label>
            <textarea className={styles.textarea} style={{ minHeight: "8rem" }} value={editBodyHtml} onChange={e => setEditBodyHtml(e.target.value)} />
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setEditTarget(null)}>{scm("cancel")}</button>
              <button className={styles.btnPrimary} disabled={editing || !editSubject || !editBodyHtml} onClick={handleEdit}>
                {editing ? scm("saving") : scm("saveChanges")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal — uses iframe sandbox to prevent XSS */}
      {previewCampaign && (
        <div className={styles.modalOverlay} onClick={() => setPreviewCampaign(null)}>
          <div className={styles.modal} style={{ width: "min(42rem, 100%)", maxHeight: "80vh", overflow: "auto" }} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{scm("previewTitle")}: {previewCampaign.subject}</h3>
            <p className={styles.modalHint}>{scm("segmentLabel")}: {SEGMENT_LABELS[previewCampaign.target_segment]}</p>
            <iframe
              title="Email preview"
              sandbox="allow-same-origin"
              srcDoc={previewCampaign.body_html}
              style={{ width: "100%", minHeight: "240px", border: "1px solid var(--bf-border)", borderRadius: "8px", background: "#fff" }}
            />
            <div className={styles.modalActions} style={{ marginTop: "0.75rem" }}>
              <button className={styles.btnNeutral} onClick={() => setPreviewCampaign(null)}>{scm("close")}</button>
            </div>
          </div>
        </div>
      )}

      {/* Send Confirm */}
      {sendTarget && (
        <div className={styles.modalOverlay} onClick={() => setSendTarget(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{scm("sendTitle")}</h3>
            <p className={styles.modalHint}>
              {scm("sendConfirm")} <strong>&quot;{sendTarget.subject}&quot;</strong>{" "}
              <strong>~{sendTarget.estimated_recipients ?? "?"} {scm("recipients")}</strong>{" "}
              <strong>{SEGMENT_LABELS[sendTarget.target_segment]}</strong>.
            </p>
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setSendTarget(null)}>{scm("cancel")}</button>
              <button className={styles.btnPrimary} disabled={sending} onClick={handleSend}>
                {sending ? scm("sending") : scm("confirmSend")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteTarget && (
        <div className={styles.modalOverlay} onClick={() => setDeleteTarget(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>{scm("deleteTitle")}</h3>
            <p className={styles.modalHint}>{scm("deleteConfirm")} <strong>&quot;{deleteTarget.subject}&quot;</strong></p>
            <div className={styles.modalActions}>
              <button className={styles.btnNeutral} onClick={() => setDeleteTarget(null)}>{scm("cancel")}</button>
              <button className={styles.btnDanger} disabled={deleting} onClick={handleDelete}>
                {deleting ? scm("deleting") : scm("delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
