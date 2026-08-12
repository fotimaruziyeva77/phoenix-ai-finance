import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";

import { ResetPasswordForm } from "./reset-password-form";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

const replaceMock = vi.fn();
const resetPasswordMock = vi.fn();
let searchParamsMap: Record<string, string | null> = {};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => ({
    get: (key: string) => searchParamsMap[key] ?? null,
  }),
}));

vi.mock("@/lib/api/auth", () => ({
  resetPassword: (...args: unknown[]) => resetPasswordMock(...args),
}));

vi.mock("@/lib/api/errors", () => ({
  parseApiErrorMessage: (e: unknown) =>
    e instanceof Error ? e.message : "Something went wrong.",
}));

vi.mock("@/contexts/language-context", () => ({
  useLanguage: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "auth.resetPassword.title": "Reset password",
        "auth.resetPassword.subtitle": "Enter your new password",
        "auth.resetPassword.password": "New password",
        "auth.resetPassword.confirmPassword": "Confirm new password",
        "auth.resetPassword.submit": "Reset password",
        "auth.resetPassword.submitting": "Resetting…",
        "auth.resetPassword.success": "Password reset successfully!",
        "auth.forgotPassword.submit": "Request reset link",
        "auth.forgotPassword.backToLogin": "Back to login",
        "auth.verify.invalid": "Invalid link",
        "auth.showPassword": "Show password",
        "auth.hidePassword": "Hide password",
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

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParamsMap = {};
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows missing-token screen when no token in URL", () => {
    searchParamsMap = {};
    render(<ResetPasswordForm />);

    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(screen.getByText("Request reset link")).toBeInTheDocument();
    expect(screen.getByText("Back to login")).toBeInTheDocument();
  });

  it("renders form when token is present", () => {
    searchParamsMap = { token: "reset-token-123" };
    render(<ResetPasswordForm />);

    expect(screen.getByText("Reset password")).toBeInTheDocument();
    expect(screen.getByLabelText("New password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reset password" }),
    ).toBeInTheDocument();
  });

  it("shows validation error when password is empty", async () => {
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "New password is required.",
    );
    expect(resetPasswordMock).not.toHaveBeenCalled();
  });

  it("shows validation error when password is too short", async () => {
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "short");
    await user.type(screen.getByLabelText("Confirm new password"), "short");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters.",
    );
    expect(resetPasswordMock).not.toHaveBeenCalled();
  });

  it("shows validation error when passwords do not match", async () => {
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "password123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "different99",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Passwords do not match.",
    );
    expect(resetPasswordMock).not.toHaveBeenCalled();
  });

  it("calls resetPassword API on valid submission", async () => {
    resetPasswordMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "my-reset-token" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "newpass123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpass123",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(resetPasswordMock).toHaveBeenCalledWith(
        "my-reset-token",
        "newpass123",
      );
    });
  });

  it("shows success screen after successful reset", async () => {
    resetPasswordMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "newpass123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpass123",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(
        screen.getByText("Password reset successfully!"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Back to login")).toBeInTheDocument();
  });

  it("redirects to login after successful reset with delay", async () => {
    resetPasswordMock.mockResolvedValueOnce(undefined);
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "newpass123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpass123",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(
        screen.getByText("Password reset successfully!"),
      ).toBeInTheDocument();
    });

    vi.advanceTimersByTime(3000);

    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("displays API error on reset failure", async () => {
    resetPasswordMock.mockRejectedValueOnce(new Error("Token expired."));
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "newpass123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpass123",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Token expired.");
    });
  });

  it("shows button as disabled with 'Resetting...' while loading", async () => {
    resetPasswordMock.mockReturnValue(new Promise(() => {})); // never resolves
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    await user.type(screen.getByLabelText("New password"), "newpass123");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "newpass123",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Resetting…" }),
      ).toBeDisabled();
    });
  });

  it("toggles password visibility for both fields", async () => {
    searchParamsMap = { token: "tok" };
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ResetPasswordForm />);

    const passwordInput = screen.getByLabelText("New password");
    const confirmInput = screen.getByLabelText("Confirm new password");
    expect(passwordInput).toHaveAttribute("type", "password");
    expect(confirmInput).toHaveAttribute("type", "password");

    const toggleButtons = screen.getAllByLabelText("Show password");
    expect(toggleButtons).toHaveLength(2);

    await user.click(toggleButtons[0]);
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(toggleButtons[1]);
    expect(confirmInput).toHaveAttribute("type", "text");
  });
});
