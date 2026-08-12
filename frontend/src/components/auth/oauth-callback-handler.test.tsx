import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { useAuth } from "@/hooks/useAuth";

import { OAuthCallbackHandler } from "./oauth-callback-handler";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

const replaceMock = vi.fn();
let searchParamsMap: Record<string, string | null> = {};

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => ({
    get: (key: string) => searchParamsMap[key] ?? null,
  }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
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
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const completeOAuthMock = vi.fn();

const baseAuth = {
  user: null,
  accessToken: null,
  refreshToken: null,
  hydrated: true,
  canUseAuthenticatedApi: false,
  busy: false,
  login: vi.fn(),
  register: vi.fn(),
  completeOAuthExchange: completeOAuthMock,
  logout: vi.fn(),
  refreshProfile: vi.fn(),
};

function setup(
  params: Record<string, string | null> = {},
  overrides: Partial<ReturnType<typeof useAuth>> = {},
) {
  searchParamsMap = params;
  vi.mocked(useAuth).mockReturnValue({ ...baseAuth, ...overrides });
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("OAuthCallbackHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchParamsMap = {};
  });

  it("shows loading state while processing exchange code", () => {
    completeOAuthMock.mockReturnValue(new Promise(() => {})); // never resolves
    setup({ oauth_exchange_code: "abc123" });
    render(<OAuthCallbackHandler />);

    expect(screen.getByText("Completing sign-in")).toBeInTheDocument();
    expect(screen.getByText("Finishing OAuth…")).toBeInTheDocument();
  });

  it("completes OAuth exchange and redirects to dashboard", async () => {
    completeOAuthMock.mockResolvedValueOnce(undefined);
    setup({ oauth_exchange_code: "valid-code" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(completeOAuthMock).toHaveBeenCalledWith("valid-code");
    });
    expect(replaceMock).toHaveBeenCalledWith("/dashboard");
  });

  it("shows error when oauth_error is present", async () => {
    setup({ oauth_error: "google_oauth_denied" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByText("Sign-in issue")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Google sign-in was cancelled.",
    );
    expect(screen.getByText("Back to sign in")).toBeInTheDocument();
  });

  it("shows error with detail when both oauth_error and oauth_error_detail are present", async () => {
    setup({
      oauth_error: "google_token_exchange_failed",
      oauth_error_detail: "redirect_uri_mismatch",
    });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "(redirect_uri_mismatch)",
      );
    });
  });

  it("shows error when exchange code is missing", async () => {
    setup({}); // no params at all
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Missing OAuth exchange code.",
      );
    });
  });

  it("shows error when exchange code is empty string", async () => {
    setup({ oauth_exchange_code: "  " });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Missing OAuth exchange code.",
      );
    });
  });

  it("shows API error when completeOAuthExchange fails", async () => {
    completeOAuthMock.mockRejectedValueOnce(
      new Error("Token exchange expired."),
    );
    setup({ oauth_exchange_code: "expired-code" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Token exchange expired.",
      );
    });
  });

  it("shows generic fallback when completeOAuthExchange throws non-Error", async () => {
    completeOAuthMock.mockRejectedValueOnce("unexpected");
    setup({ oauth_exchange_code: "some-code" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Could not complete sign-in.",
      );
    });
  });

  it("does not call completeOAuthExchange when not hydrated", () => {
    setup({ oauth_exchange_code: "abc" }, { hydrated: false });
    render(<OAuthCallbackHandler />);

    expect(completeOAuthMock).not.toHaveBeenCalled();
    // Should show loading state
    expect(screen.getByText("Completing sign-in")).toBeInTheDocument();
  });

  it("renders known GitHub error code", async () => {
    setup({ oauth_error: "github_oauth_denied" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "GitHub sign-in was cancelled.",
      );
    });
  });

  it("renders unknown error code with fallback format", async () => {
    setup({ oauth_error: "some_unknown_error" });
    render(<OAuthCallbackHandler />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Sign-in failed (some_unknown_error).",
      );
    });
  });
});
