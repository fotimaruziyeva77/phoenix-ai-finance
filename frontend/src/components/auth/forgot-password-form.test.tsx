import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ForgotPasswordForm } from "./forgot-password-form";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

const forgotPasswordMock = vi.fn();

vi.mock("@/lib/api/auth", () => ({
  forgotPassword: (...args: unknown[]) => forgotPasswordMock(...args),
}));

vi.mock("@/lib/api/errors", () => ({
  parseApiErrorMessage: (e: unknown) =>
    e instanceof Error ? e.message : "Something went wrong.",
}));

vi.mock("@/contexts/language-context", () => ({
  useLanguage: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "auth.forgotPassword.title": "Forgot password",
        "auth.forgotPassword.subtitle": "Enter your email to reset",
        "auth.forgotPassword.email": "Email",
        "auth.forgotPassword.submit": "Send reset link",
        "auth.forgotPassword.submitting": "Sending…",
        "auth.forgotPassword.success": "Check your email for a reset link.",
        "auth.forgotPassword.backToLogin": "Back to login",
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

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("ForgotPasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without errors", () => {
    render(<ForgotPasswordForm />);

    expect(screen.getByText("Forgot password")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Send reset link" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Back to login")).toBeInTheDocument();
  });

  it("shows validation error when email is empty", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email address is required.",
    );
    expect(forgotPasswordMock).not.toHaveBeenCalled();
  });

  it("shows validation error for invalid email", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "not-valid");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid email address.",
    );
    expect(forgotPasswordMock).not.toHaveBeenCalled();
  });

  it("calls forgotPassword API on valid submission", async () => {
    forgotPasswordMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(forgotPasswordMock).toHaveBeenCalledWith("test@example.com");
    });
  });

  it("shows success screen after successful submission", async () => {
    forgotPasswordMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(
        screen.getByText("Check your email for a reset link."),
      ).toBeInTheDocument();
    });
    // Form should be gone, only back-to-login link remains
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    expect(screen.getByText("Back to login")).toBeInTheDocument();
  });

  it("shows button text as 'Sending...' while loading", async () => {
    forgotPasswordMock.mockReturnValue(new Promise(() => {})); // never resolves
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    });
  });

  it("displays API error on network/server failure", async () => {
    forgotPasswordMock.mockRejectedValueOnce(new Error("Network error"));
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Network error");
    });
    // Form should still be visible for retry
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });

  it("trims email whitespace before sending", async () => {
    forgotPasswordMock.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText("Email"), "  test@example.com  ");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(forgotPasswordMock).toHaveBeenCalledWith("test@example.com");
    });
  });
});
