import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { useAuth } from "@/hooks/useAuth";

import { SignupForm } from "./signup-form";

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
        "auth.signup.title": "Create account",
        "auth.signup.subtitle": "Get started with BotForge",
        "auth.signup.name": "Full name",
        "auth.signup.nameOptional": "(optional)",
        "auth.signup.email": "Email",
        "auth.signup.password": "Password",
        "auth.signup.confirmPassword": "Confirm password",
        "auth.signup.submit": "Create account",
        "auth.signup.submitting": "Creating…",
        "auth.signup.haveAccount": "Already have an account?",
        "auth.signup.signIn": "Sign in",
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

const registerMock = vi.fn();

const baseAuth = {
  user: null,
  accessToken: null,
  refreshToken: null,
  hydrated: true,
  canUseAuthenticatedApi: false,
  busy: false,
  login: vi.fn(),
  register: registerMock,
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

describe("SignupForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without errors", () => {
    setup();
    render(<SignupForm />);
    expect(screen.getByText("Create account")).toBeInTheDocument();
    expect(screen.getByLabelText(/Full name/)).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });

  it("shows validation error when required fields are empty", async () => {
    const user = setup();
    render(<SignupForm />);

    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Email and both password fields are required.",
    );
    expect(registerMock).not.toHaveBeenCalled();
  });

  it("shows validation error for invalid email format", async () => {
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "bad-email");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid email address.",
    );
    expect(registerMock).not.toHaveBeenCalled();
  });

  it("shows validation error when password is too short", async () => {
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.type(screen.getByLabelText("Confirm password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters.",
    );
    expect(registerMock).not.toHaveBeenCalled();
  });

  it("shows validation error when passwords do not match", async () => {
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "different99");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Passwords do not match.",
    );
    expect(registerMock).not.toHaveBeenCalled();
  });

  it("disables submit button when not hydrated", () => {
    setup({ hydrated: false });
    render(<SignupForm />);
    expect(screen.getByRole("button", { name: "Creating…" })).toBeDisabled();
  });

  it("disables submit button when busy", () => {
    setup({ busy: true });
    render(<SignupForm />);
    expect(screen.getByRole("button", { name: "Creating…" })).toBeDisabled();
  });

  it("calls register and redirects on successful submission", async () => {
    registerMock.mockResolvedValueOnce(undefined);
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith(
        "test@example.com",
        "password123",
        undefined,
      );
    });
    expect(replaceMock).toHaveBeenCalled();
  });

  it("passes full name to register when provided", async () => {
    registerMock.mockResolvedValueOnce(undefined);
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText(/Full name/), "John Doe");
    await user.type(screen.getByLabelText("Email"), "john@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith(
        "john@example.com",
        "password123",
        "John Doe",
      );
    });
  });

  it("displays API error on registration failure", async () => {
    registerMock.mockRejectedValueOnce(new Error("Email already exists."));
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Email already exists.",
      );
    });
  });

  it("displays generic fallback on non-Error rejection", async () => {
    registerMock.mockRejectedValueOnce("server error");
    const user = setup();
    render(<SignupForm />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.type(screen.getByLabelText("Confirm password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Could not create account.",
      );
    });
  });

  it("toggles password visibility for both password fields", async () => {
    const user = setup();
    render(<SignupForm />);

    const passwordInput = screen.getByLabelText("Password");
    const confirmInput = screen.getByLabelText("Confirm password");
    expect(passwordInput).toHaveAttribute("type", "password");
    expect(confirmInput).toHaveAttribute("type", "password");

    // There are two toggle buttons — use getAllByLabelText
    const toggleButtons = screen.getAllByLabelText("Show password");
    expect(toggleButtons).toHaveLength(2);

    await user.click(toggleButtons[0]);
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(toggleButtons[1]);
    expect(confirmInput).toHaveAttribute("type", "text");
  });
});
