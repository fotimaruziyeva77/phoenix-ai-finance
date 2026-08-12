import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { useAuth } from "@/hooks/useAuth";

import { LoginForm } from "./login-form";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => ({
    get: () => null,
  }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/contexts/language-context", () => ({
  useLanguage: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "auth.login.title": "Sign in",
        "auth.login.subtitle": "Welcome back",
        "auth.login.email": "Email",
        "auth.login.password": "Password",
        "auth.login.submit": "Sign in",
        "auth.login.submitting": "Signing in…",
        "auth.login.forgotPassword": "Forgot password?",
        "auth.login.noAccount": "No account?",
        "auth.login.createOne": "Create one",
        "auth.showPassword": "Show password",
        "auth.hidePassword": "Hide password",
        "auth.oauth.google": "Google",
        "auth.oauth.github": "GitHub",
      };
      return map[key] ?? key;
    },
  }),
}));

vi.mock("./auth-page-shell", () => ({
  AuthPageShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="auth-page-shell">
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("./oauth-provider-buttons", () => ({
  OAuthProviderButtons: () => <div data-testid="oauth-buttons">oauth</div>,
}));

vi.mock("./auth-shell.module.css", () => ({
  default: new Proxy({}, { get: (_, key) => `mock-${String(key)}` }),
}));

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const loginMock = vi.fn();

const baseAuth = {
  user: null,
  accessToken: null,
  refreshToken: null,
  hydrated: true,
  canUseAuthenticatedApi: false,
  busy: false,
  login: loginMock,
  register: vi.fn(),
  completeOAuthExchange: vi.fn(),
  logout: vi.fn(),
  refreshProfile: vi.fn(),
};

function setup(overrides: Partial<ReturnType<typeof useAuth>> = {}) {
  vi.mocked(useAuth).mockReturnValue({ ...baseAuth, ...overrides });
  return userEvent.setup();
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without errors", () => {
    setup();
    render(<LoginForm />);
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByTestId("oauth-buttons")).toBeInTheDocument();
  });

  it("shows validation error when fields are empty", async () => {
    const user = setup();
    render(<LoginForm />);

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email and password are required.",
    );
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("shows validation error for invalid email", async () => {
    const user = setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.type(screen.getByLabelText("Password"), "secret123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid email address.",
    );
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("shows validation when only email is provided", async () => {
    const user = setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email and password are required.",
    );
  });

  it("disables submit button when not hydrated", () => {
    setup({ hydrated: false });
    render(<LoginForm />);

    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
  });

  it("disables submit button when busy", () => {
    setup({ busy: true });
    render(<LoginForm />);

    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
  });

  it("calls login and redirects on successful submission", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    const user = setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith("test@example.com", "password123");
    });
    expect(replaceMock).toHaveBeenCalled();
  });

  it("displays API error on login failure", async () => {
    loginMock.mockRejectedValueOnce(new Error("Invalid credentials."));
    const user = setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Invalid credentials.",
      );
    });
  });

  it("displays generic fallback on non-Error rejection", async () => {
    loginMock.mockRejectedValueOnce("network issue");
    const user = setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Sign-in failed.");
    });
  });

  it("toggles password visibility", async () => {
    const user = setup();
    render(<LoginForm />);

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("type", "password");

    const toggleBtn = screen.getByLabelText("Show password");
    await user.click(toggleBtn);

    expect(passwordInput).toHaveAttribute("type", "text");
    expect(screen.getByLabelText("Hide password")).toBeInTheDocument();
  });

  it("clears validation error after correcting input and resubmitting", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    const user = setup();
    render(<LoginForm />);

    // First submit — empty fields
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email and password are required.",
    );

    // Fill in fields and re-submit
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalled();
    });
  });
});
