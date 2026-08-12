/**
 * Typed fetch wrapper for the backend API.
 * Base URL: NEXT_PUBLIC_API_BASE_URL (required for same-origin-relative paths to work against API).
 *
 * Sends ``X-Request-ID`` / ``X-Correlation-ID`` so API logs and JSON errors align with the browser.
 */

import { authCookieMode, authCsrfHeaderName } from "@/lib/auth/cookie-mode";
import { getCsrfToken } from "@/lib/auth/csrf";
import { readStoredSession, writeStoredSession, clearStoredSession } from "@/lib/auth/storage";
import { getOrCreateCorrelationId } from "@/lib/observability/correlation";

// ─── Token refresh state (singleton, prevents concurrent refresh races) ──────

let _refreshPromise: Promise<string | null> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns the new access token or ``null`` on failure.
 * Concurrent callers share the same in-flight promise (de-dup).
 */
async function _tryRefreshAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    try {
      const stored = readStoredSession();
      if (!stored?.refreshToken) return null;

      const res = await fetch(resolveUrl("/api/v1/auth/refresh"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({ refresh_token: stored.refreshToken }),
      });

      if (!res.ok) {
        clearStoredSession();
        return null;
      }

      const data = (await res.json()) as {
        access_token?: string | null;
        refresh_token?: string | null;
      };
      const newAccess = data.access_token;
      const newRefresh = data.refresh_token;
      if (!newAccess) {
        clearStoredSession();
        return null;
      }

      writeStoredSession({
        accessToken: newAccess,
        refreshToken: newRefresh ?? stored.refreshToken,
        user: stored.user,
      });
      return newAccess;
    } catch {
      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: string;
  readonly requestId?: string | null;
  readonly correlationId?: string | null;

  constructor(
    status: number,
    body: string,
    meta?: { requestId?: string | null; correlationId?: string | null },
  ) {
    super(`API ${status}: ${body || "(empty body)"}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.requestId = meta?.requestId;
    this.correlationId = meta?.correlationId;
  }
}

function resolveUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

export type ApiFetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

/** Mutates ``target``; returns correlation id used (for error mapping). */
function applyCorrelationHeaders(target: Headers): string {
  const correlationId = getOrCreateCorrelationId();
  const requestId =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `bf-req-${Date.now()}`;
  if (!target.has("X-Correlation-ID")) {
    target.set("X-Correlation-ID", correlationId);
  }
  if (!target.has("X-Request-ID")) {
    target.set("X-Request-ID", requestId);
  }
  // Bypass ngrok free-tier browser interstitial that strips CORS headers.
  target.set("ngrok-skip-browser-warning", "true");
  return correlationId;
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { body, headers, ...rest } = options;
  const initHeaders = new Headers(headers ?? undefined);

  let bodyInit: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    if (!initHeaders.has("Content-Type")) {
      initHeaders.set("Content-Type", "application/json");
    }
    bodyInit = typeof body === "string" ? body : JSON.stringify(body);
  }

  const method = (rest.method ?? "GET").toUpperCase();
  const cookieMode = authCookieMode();
  if (cookieMode) {
    const csrf = getCsrfToken();
    if (csrf && !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      initHeaders.set(authCsrfHeaderName(), csrf);
    }
  }

  const correlationId = applyCorrelationHeaders(initHeaders);

  const response = await fetch(resolveUrl(path), {
    ...rest,
    credentials: cookieMode ? "include" : rest.credentials,
    headers: initHeaders,
    body: bodyInit,
  });

  const text = await response.text();

  if (!response.ok) {
    const hdrRid = response.headers.get("x-request-id") ?? response.headers.get("X-Request-ID");
    const hdrCid = response.headers.get("x-correlation-id") ?? response.headers.get("X-Correlation-ID");
    let bodyRid: string | null | undefined;
    try {
      const j = JSON.parse(text) as { error?: { request_id?: string | null } };
      bodyRid = j?.error?.request_id;
    } catch {
      bodyRid = undefined;
    }
    throw new ApiError(response.status, text, {
      requestId: bodyRid ?? hdrRid,
      correlationId: hdrCid ?? correlationId,
    });
  }

  if (text.length === 0) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return JSON.parse(text) as T;
  }

  return text as T;
}

/** Attach Bearer token for authenticated routes; auto-retries once on 401 after refresh. */
/**
 * Prefer the freshest access token from storage (kept current by ``_tryRefreshAccessToken``)
 * over the ``accessToken`` argument, which often comes from React state that lags a refresh.
 * Using the stored token avoids a 401 → refresh → retry round-trip on every call once any
 * call has refreshed. In cookie mode there is no bearer token, so the argument is used as-is.
 */
function _freshAccessToken(passed: string | null): string | null {
  if (authCookieMode()) return passed;
  return readStoredSession()?.accessToken ?? passed;
}

export async function apiFetchWithAuth<T>(
  path: string,
  accessToken: string | null,
  options: ApiFetchOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers ?? undefined);
  const effectiveToken = _freshAccessToken(accessToken);
  if (effectiveToken) {
    headers.set("Authorization", `Bearer ${effectiveToken}`);
  }
  const cookieMode = authCookieMode();
  try {
    return await apiFetch<T>(path, {
      ...options,
      headers,
      credentials: cookieMode ? "include" : options.credentials,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401 && !cookieMode) {
      const newToken = await _tryRefreshAccessToken();
      if (newToken) {
        const retryHeaders = new Headers(options.headers ?? undefined);
        retryHeaders.set("Authorization", `Bearer ${newToken}`);
        return apiFetch<T>(path, {
          ...options,
          headers: retryHeaders,
          credentials: options.credentials,
        });
      }
    }
    throw err;
  }
}

/** Multipart upload: do not set ``Content-Type`` (browser sets boundary). */
export async function apiUploadWithAuth<T>(
  path: string,
  accessToken: string | null,
  file: File,
  fieldName = "file",
): Promise<T> {
  const formData = new FormData();
  formData.append(fieldName, file);
  const headers = new Headers();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const cookieMode = authCookieMode();
  const csrf = getCsrfToken();
  if (cookieMode && csrf) {
    headers.set(authCsrfHeaderName(), csrf);
  }
  const correlationId = applyCorrelationHeaders(headers);
  const response = await fetch(resolveUrl(path), {
    method: "POST",
    headers,
    body: formData,
    credentials: cookieMode ? "include" : undefined,
  });
  const text = await response.text();
  if (!response.ok) {
    const hdrRid = response.headers.get("x-request-id") ?? response.headers.get("X-Request-ID");
    const hdrCid = response.headers.get("x-correlation-id") ?? response.headers.get("X-Correlation-ID");
    let bodyRid: string | null | undefined;
    try {
      const j = JSON.parse(text) as { error?: { request_id?: string | null } };
      bodyRid = j?.error?.request_id;
    } catch {
      bodyRid = undefined;
    }
    throw new ApiError(response.status, text, {
      requestId: bodyRid ?? hdrRid,
      correlationId: hdrCid ?? correlationId,
    });
  }
  if (text.length === 0) {
    return undefined as T;
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return JSON.parse(text) as T;
  }
  return text as T;
}

async function _fetchBlobOnce(path: string, accessToken: string | null): Promise<Response> {
  const headers = new Headers();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  applyCorrelationHeaders(headers); // adds ngrok-skip-browser-warning + request/correlation ids
  const cookieMode = authCookieMode();
  return fetch(resolveUrl(path), {
    method: "GET",
    headers,
    credentials: cookieMode ? "include" : undefined,
  });
}

/**
 * Authenticated binary download (e.g. CSV export). Mirrors :func:`apiFetchWithAuth`'s
 * 401 → refresh → retry so a stale access token does not fail the download, and returns the
 * response body as a ``Blob`` instead of parsing JSON.
 */
export async function downloadBlobWithAuth(
  path: string,
  accessToken: string | null,
): Promise<Blob> {
  const cookieMode = authCookieMode();
  let res = await _fetchBlobOnce(path, _freshAccessToken(accessToken));
  if (res.status === 401 && !cookieMode) {
    const newToken = await _tryRefreshAccessToken();
    if (newToken) {
      res = await _fetchBlobOnce(path, newToken);
    }
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body);
  }
  return res.blob();
}

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
}
