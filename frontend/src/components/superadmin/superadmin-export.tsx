"use client";

import { useState } from "react";

import { useLanguage } from "@/contexts/language-context";
import { useAuth } from "@/hooks/useAuth";
import { downloadBlobWithAuth } from "@/lib/api/client";

import styles from "./superadmin.module.css";

type ExportKey = "users" | "subscriptions" | "aiUsage" | "coupons";

type ExportItem = {
  key: ExportKey;
  filename: string;
  endpoint: string;
};

const PRESETS = [
  { key: "7d", days: 7 },
  { key: "30d", days: 30 },
  { key: "90d", days: 90 },
  { key: "ytd", days: 0 }, // special: year-to-date
];

const EXPORTS: ExportItem[] = [
  { key: "users",         filename: "users.csv",         endpoint: "/api/v1/admin/export/users.csv" },
  { key: "subscriptions", filename: "subscriptions.csv", endpoint: "/api/v1/admin/export/subscriptions.csv" },
  { key: "aiUsage",       filename: "ai_usage.csv",      endpoint: "/api/v1/admin/export/ai-usage.csv" },
  { key: "coupons",       filename: "coupons.csv",       endpoint: "/api/v1/admin/export/coupons.csv" },
];

export function SuperadminExport() {
  const { accessToken: token } = useAuth();
  const { t } = useLanguage();

  const se = (key: string) => String(t(`superadmin.export.${key}`));
  const sc = (key: string) => String(t(`superadmin.common.${key}`));

  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [sinceDate, setSinceDate] = useState("");
  const [untilDate, setUntilDate] = useState("");

  function applyPreset(preset: { key: string; days: number }) {
    const now = new Date();
    if (preset.key === "ytd") {
      setSinceDate(`${now.getFullYear()}-01-01`);
    } else {
      const since = new Date(now);
      since.setDate(since.getDate() - preset.days);
      setSinceDate(since.toISOString().slice(0, 10));
    }
    setUntilDate(now.toISOString().slice(0, 10));
  }

  async function handleDownload(item: ExportItem) {
    if (!token) return;
    setDownloading(item.filename);
    setError("");
    try {
      let url = item.endpoint;
      const params = new URLSearchParams();
      if (sinceDate) params.set("since", new Date(sinceDate).toISOString());
      if (untilDate) params.set("until", new Date(untilDate + "T23:59:59").toISOString());
      const qs = params.toString();
      if (qs) url += `?${qs}`;
      // Uses the shared auth fetch so a stale access token is refreshed + retried
      // (raw fetch here previously failed the download with HTTP 401).
      const blob = await downloadBlobWithAuth(url, token);
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = item.filename;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch (e: unknown) {
      setError(`${se("downloadFailed")} ${se(`${item.key}Label`)}: ${e instanceof Error ? e.message : sc("error")}`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className={styles.stack}>
      <p className={styles.pageIntro}>
        {se("intro")}
      </p>
      {error && <p className={styles.errorBanner}>{error}</p>}

      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.5rem", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.85rem", color: "var(--bf-text-muted)" }}>{se("quickPresets")}:</span>
        {PRESETS.map(p => (
          <button
            key={p.key}
            className={styles.pageBtn}
            onClick={() => applyPreset(p)}
            style={{ fontSize: "0.78rem" }}
          >
            {se(`preset${p.key.charAt(0).toUpperCase() + p.key.slice(1)}`)}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap" }}>
        <label style={{ fontSize: "0.85rem", color: "var(--bf-text-muted)" }}>Date range:</label>
        <input type="date" value={sinceDate} onChange={e => setSinceDate(e.target.value)} className={styles.filterInput} />
        <span style={{ color: "var(--bf-text-muted)" }}>&mdash;</span>
        <input type="date" value={untilDate} onChange={e => setUntilDate(e.target.value)} className={styles.filterInput} />
        {(sinceDate || untilDate) && (
          <button onClick={() => { setSinceDate(""); setUntilDate(""); }} className={styles.pageBtn}>
            {sc("clear")} ✕
          </button>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(16rem, 1fr))", gap: "0.85rem" }}>
        {EXPORTS.map(item => (
          <div
            key={item.filename}
            className={styles.statCard}
            style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}
          >
            <div>
              <p style={{ margin: "0 0 0.2rem", fontWeight: 700, fontSize: "0.95rem" }}>{se(`${item.key}Label`)}</p>
              <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--bf-text-muted)", lineHeight: 1.4 }}>
                {se(`${item.key}Desc`)}
              </p>
            </div>
            <div style={{ marginTop: "auto", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <code style={{ fontSize: "0.7rem", color: "var(--bf-text-muted)" }}>{item.filename}</code>
              <button
                className={styles.btnPrimary}
                disabled={downloading === item.filename}
                onClick={() => handleDownload(item)}
              >
                {downloading === item.filename ? se("downloading") : se("download")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
