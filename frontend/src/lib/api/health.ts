import type { HealthStatus } from "@/types/api";

/**
 * GET ``/api/v1/health`` using the configured API base URL.
 *
 * Falls back to a relative fetch when ``NEXT_PUBLIC_API_BASE_URL`` is unset.
 */
export async function fetchBackendHealth(): Promise<HealthStatus> {
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
  const url = `${base}/api/v1/health`;

  const response = await fetch(url, {
    method: "GET",
    headers: { "ngrok-skip-browser-warning": "true" },
  });

  const text = await response.text();
  if (!response.ok) {
    throw new Error(text ? `API ${response.status}: ${text.slice(0, 120)}` : `API ${response.status}`);
  }
  if (!text) {
    throw new Error("Empty health response");
  }
  return JSON.parse(text) as HealthStatus;
}
