import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { VerifyEmailForm } from "./verify-email-form";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

let searchParamsMap: Record<string, string | null> = {};

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => searchParamsMap[key] ?? null,
  }),
}));

vi.mock("@/contexts/language-context", () => ({
  useLanguage: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "auth.verify.title": "Verifying email",
        "auth.verify.success": "Email verified successfully!",
        "auth.verify.invalid": "Invalid verification link",
        "auth.forgotPassword.backToLogin": "Back to login",
        "auth.login.submit": "Sign in",
      };
      return map[key] ?? key;
    },
  }),
}));

vi.mock("./auth-page-shell", () => ({
  AuthPageShell: ({
    children,
    title,
    subtitle,
  }: {
    children?: React.ReactNode;
    title: string;
    subtitle?: string;
  }) => (
    <div data-testid="auth-page-shell">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {children}
    </div>
  ),
}));

vi.mock("./auth-shell.module.css", () => ({
  default: new Proxy({}, { get: (_, key) => `mock-${String(key)}` }),
}));

const apiFetchMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    body: string;
    constructor(status: number, body: string) {
      super(`API ${status}`);
      this.name = "ApiError";
      this.status = status;
      this.body = body;
    }
  },
}));

vi.mock("@/lib/api/errors", () => ({
  parseApiErrorMessage: (error: unknown) => {
    if (error && typeof error === "object" && "body" in error) {
      try {
        const j = JSON.parse((error as { body: string }).body) as {
          error?: { message?: string };
        };
        if (j.error?.message) return j.error.message;
      } catch {
        /* fallback */
      }
    }
    if (error instanceof Error) return error.message;
    return "Something went wrong.";
  },
}));

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("VerifyEmailForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParamsMap = {};
  });

  it("shows missing-token screen when no token in URL", () => {
    searchParamsMap = {};
    render(<VerifyEmailForm />);

    expect(screen.getByText("Invalid verification link")).toBeInTheDocument();
    expect(screen.getByText("Back to login")).toBeInTheDocument();
  });

  it("shows loading state while verifying", () => {
    apiFetchMock.mockReturnValue(new Promise(() => {})); // never resolves
    searchParamsMap = { token: "valid-token" };
    render(<VerifyEmailForm />);

    expect(screen.getByText("Verifying email")).toBeInTheDocument();
  });

  it("shows success screen after successful verification", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "valid-token" };
    render(<VerifyEmailForm />);

    await waitFor(() => {
      expect(
        screen.getByText("Email verified successfully!"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  it("calls API with correct endpoint and token", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "my-token-123" };
    render(<VerifyEmailForm />);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/auth/verify-email", {
        method: "POST",
        body: { token: "my-token-123" },
      });
    });
  });

  it("shows error when verification fails", async () => {
    const mockError = Object.assign(new Error("API 400"), {
      name: "ApiError",
      status: 400,
      body: JSON.stringify({ error: { message: "Token expired." } }),
    });
    apiFetchMock.mockRejectedValueOnce(mockError);
    searchParamsMap = { token: "expired-token" };
    render(<VerifyEmailForm />);

    await waitFor(() => {
      expect(
        screen.getByText("Invalid verification link"),
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Token expired.");
  });

  it("does not call API twice on re-render (calledRef guard)", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "once-token" };

    const { rerender } = render(<VerifyEmailForm />);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(1);
    });

    // Force re-render
    rerender(<VerifyEmailForm />);

    // Still called only once
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
