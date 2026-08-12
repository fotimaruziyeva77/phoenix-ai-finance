"use client";

import { useEffect, useState } from "react";

type TokenEntry = {
  type: "email_verify" | "password_reset";
  token: string;
  user_id: string;
  ttl_seconds_remaining: number;
  action_url: string;
};

type DevTokensResponse = {
  environment: string;
  redis_available: boolean;
  count: number;
  tokens: TokenEntry[];
};

/**
 * DEV-ONLY: shows pending email tokens from the backend when Resend
 * can't deliver (sandbox mode). Renders nothing in production.
 */
export function DevEmailTokens() {
  const [data, setData] = useState<DevTokensResponse | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
    fetch(`${base}/api/v1/auth/dev/pending-tokens`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: DevTokensResponse | null) => {
        if (d && d.redis_available && d.count > 0) {
          setData(d);
          setOpen(true);
        }
      })
      .catch(() => null);
  }, []);

  if (!data || data.count === 0) return null;

  return (
    <div style={{
      marginTop: "1.25rem",
      border: "1.5px dashed #f59e0b",
      borderRadius: "10px",
      background: "#fffbeb",
      padding: "0.85rem 1rem",
      fontSize: "0.8rem",
      color: "#92400e",
    }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "none", border: "none", cursor: "pointer",
          fontWeight: 700, fontSize: "0.8rem", color: "#b45309",
          padding: 0, display: "flex", alignItems: "center", gap: "0.4rem",
          width: "100%",
        }}
      >
        <span>🛠 Dev mode — email yetkazilmadi ({data.count} ta link)</span>
        <span style={{ marginLeft: "auto" }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{ marginTop: "0.6rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {data.tokens.map((t, i) => (
            <div key={i} style={{
              background: "#fef3c7", borderRadius: "6px",
              padding: "0.5rem 0.65rem",
            }}>
              <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>
                {t.type === "email_verify" ? "✉️ Email tasdiqlash" : "🔑 Parol tiklash"}
                <span style={{ fontWeight: 400, opacity: 0.7, marginLeft: "0.4rem" }}>
                  (TTL: {t.ttl_seconds_remaining}s)
                </span>
              </div>
              <a
                href={t.action_url}
                style={{
                  color: "#1d4ed8", wordBreak: "break-all",
                  fontSize: "0.75rem", textDecoration: "underline",
                }}
              >
                {t.action_url}
              </a>
            </div>
          ))}
          <p style={{ margin: "0.25rem 0 0", opacity: 0.65, fontSize: "0.72rem" }}>
            Bu panel faqat docker/dev muhitida ko&apos;rinadi. Resend domenini tasdiqlang — o&apos;chadi.
          </p>
        </div>
      )}
    </div>
  );
}
