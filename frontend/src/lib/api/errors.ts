import { ApiError } from "./client";

/**
 * Backend ``StandardErrorResponse`` (see ``app/core/error_response.py``).
 * Auth routes set ``category: "authentication"`` for domain errors; HTTP 429 from auth uses
 * ``code: "rate_limit_exceeded"``. Full machine codes: ``app/schemas/auth_contract.py``.
 */
export type StandardErrorBody = {
  error?: {
    code?: string;
    message?: string;
    request_id?: string | null;
    category?: string | null;
    ai_category?: string | null;
    details?: unknown;
  };
};

export type ParsedApiError = {
  message: string;
  code?: string;
  aiCategory?: string;
  retryable?: boolean;
  requestId?: string | null;
  correlationId?: string | null;
};

export function parseStandardApiError(error: unknown): ParsedApiError {
  if (error instanceof ApiError) {
    try {
      const j = JSON.parse(error.body) as StandardErrorBody;
      const e = j.error;
      if (e?.message) {
        const retryableFromDetails =
          e.details !== null &&
          typeof e.details === "object" &&
          "retryable" in e.details &&
          typeof (e.details as { retryable?: unknown }).retryable === "boolean"
            ? (e.details as { retryable: boolean }).retryable
            : undefined;
        const retryableFromCode = e.code === "database_unavailable";
        return {
          message: e.message,
          code: e.code,
          aiCategory: e.ai_category ?? undefined,
          retryable: retryableFromCode ? true : retryableFromDetails,
          requestId: e.request_id ?? error.requestId,
          correlationId: error.correlationId,
        };
      }
    } catch {
      /* fall through */
    }
    if (error.body.trim()) {
      return {
        message: error.body.trim(),
        requestId: error.requestId,
        correlationId: error.correlationId,
      };
    }
    return {
      message: error.message,
      requestId: error.requestId,
      correlationId: error.correlationId,
    };
  }
  if (error instanceof Error) return { message: error.message };
  return { message: "Something went wrong." };
}

/** User-visible line for dashboard test chat (server message is already sanitized). */
export function formatAiChatErrorForUser(parsed: ParsedApiError): string {
  const m = parsed.message.trim();
  if (parsed.retryable) {
    return `${m} You can try again in a few seconds.`;
  }
  return m;
}

/** Extract server ``error.message`` (or fallback). For dashboard test chat, use ``formatAiChatErrorForUser`` after ``parseStandardApiError``. */
export function parseApiErrorMessage(error: unknown): string {
  return parseStandardApiError(error).message;
}
