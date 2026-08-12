import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { formatAiChatErrorForUser, parseApiErrorMessage, parseStandardApiError } from "./errors";

describe("parseApiErrorMessage", () => {
  it("reads FastAPI standard envelope", () => {
    const err = new ApiError(
      401,
      JSON.stringify({
        error: { code: "invalid_credentials", message: "Invalid email or password" },
      }),
    );
    expect(parseApiErrorMessage(err)).toBe("Invalid email or password");
  });

  it("falls back to raw body when JSON missing", () => {
    const err = new ApiError(500, "upstream failure");
    expect(parseApiErrorMessage(err)).toBe("upstream failure");
  });

  it("handles non-ApiError", () => {
    expect(parseApiErrorMessage(new Error("x"))).toBe("x");
  });
});

describe("parseStandardApiError + formatAiChatErrorForUser", () => {
  it("parses ai_category and retryable from envelope", () => {
    const err = new ApiError(
      503,
      JSON.stringify({
        error: {
          code: "ai_provider_unavailable",
          message: "The AI service is temporarily unavailable.",
          category: "ai_chat",
          ai_category: "provider_unavailable",
          details: { retryable: true, provider_error_code: "provider_error" },
        },
      }),
    );
    const p = parseStandardApiError(err);
    expect(p.aiCategory).toBe("provider_unavailable");
    expect(p.retryable).toBe(true);
    expect(formatAiChatErrorForUser(p)).toContain("try again");
  });
});
