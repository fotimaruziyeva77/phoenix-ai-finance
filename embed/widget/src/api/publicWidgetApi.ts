import type {
  PublicChatRequest,
  PublicChatResponse,
  StandardApiError,
  WidgetBootstrap,
} from "../types";

function trimBase(url: string): string {
  return url.replace(/\/+$/, "");
}

function extractErrorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "error" in data) {
    const err = (data as StandardApiError).error;
    if (err?.message && typeof err.message === "string") {
      return err.message;
    }
  }
  return fallback;
}

export class PublicWidgetApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "PublicWidgetApiError";
    this.status = status;
    this.code = code;
  }
}

export async function fetchWidgetBootstrap(
  apiBaseUrl: string,
  publicWidgetKey: string,
  signal?: AbortSignal,
): Promise<WidgetBootstrap> {
  const base = trimBase(apiBaseUrl);
  const url = `${base}/api/v1/public/widget/${encodeURIComponent(publicWidgetKey)}/bootstrap`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "omit",
    headers: { Accept: "application/json" },
    signal,
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const msg = extractErrorMessage(data, "Could not load chat.");
    const code =
      data && typeof data === "object" && "error" in data
        ? (data as StandardApiError).error?.code
        : undefined;
    throw new PublicWidgetApiError(msg, res.status, code);
  }
  return data as WidgetBootstrap;
}

export async function postPublicChat(
  apiBaseUrl: string,
  publicWidgetKey: string,
  body: PublicChatRequest,
  signal?: AbortSignal,
): Promise<PublicChatResponse> {
  const base = trimBase(apiBaseUrl);
  const url = `${base}/api/v1/public/widget/${encodeURIComponent(publicWidgetKey)}/chat`;
  const res = await fetch(url, {
    method: "POST",
    credentials: "omit",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: body.message,
      visitor_session_key: body.visitor_session_key ?? undefined,
      conversation_id: body.conversation_id ?? undefined,
    }),
    signal,
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const msg = extractErrorMessage(data, "Message could not be sent.");
    const code =
      data && typeof data === "object" && "error" in data
        ? (data as StandardApiError).error?.code
        : undefined;
    throw new PublicWidgetApiError(msg, res.status, code);
  }
  return data as PublicChatResponse;
}
