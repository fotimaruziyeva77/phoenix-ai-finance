import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import * as authApi from "@/lib/api/auth";
import * as cookieMode from "@/lib/auth/cookie-mode";
import * as csrfLib from "@/lib/auth/csrf";
import * as storageLib from "@/lib/auth/storage";
import type { AuthSession, AuthUser, StoredAuthSession } from "@/types/auth";

import { AuthProvider, useAuthContext } from "./auth-context";

/* ------------------------------------------------------------------ */
/*  Mocks                                                              */
/* ------------------------------------------------------------------ */

vi.mock("@/lib/auth/cookie-mode", () => ({
  authCookieMode: vi.fn(() => false),
}));

vi.mock("@/lib/auth/csrf", () => ({
  setCsrfToken: vi.fn(),
  getCsrfToken: vi.fn(() => null),
}));

vi.mock("@/lib/auth/storage", () => ({
  readStoredSession: vi.fn(() => null),
  writeStoredSession: vi.fn(),
  clearStoredSession: vi.fn(),
}));

vi.mock("@/lib/api/auth", () => ({
  loginWithEmail: vi.fn(),
  registerAccount: vi.fn(),
  exchangeOAuthCode: vi.fn(),
  fetchCurrentUser: vi.fn(),
  fetchAuthBootstrap: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  apiFetchWithAuth: vi.fn(),
}));

vi.mock("@/lib/api/errors", () => ({
  parseApiErrorMessage: (e: unknown) =>
    e instanceof Error ? e.message : "Something went wrong.",
}));

/* ------------------------------------------------------------------ */
/*  Fixtures                                                           */
/* ------------------------------------------------------------------ */

const fakeUser: AuthUser = {
  id: "u1",
  email: "test@example.com",
  full_name: "Test User",
  role: "customer_admin",
  is_active: true,
  is_verified: true,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const fakeSession: AuthSession = {
  auth_transport: "bearer",
  user: fakeUser,
  access_token: "at-123",
  refresh_token: "rt-456",
  token_type: "Bearer",
  expires_in: 3600,
  csrf_token: null,
};

const fakeStored: StoredAuthSession = {
  accessToken: "at-stored",
  refreshToken: "rt-stored",
  user: fakeUser,
};

/* ------------------------------------------------------------------ */
/*  Consumer component to read context values                          */
/* ------------------------------------------------------------------ */

function AuthConsumer({
  onContext,
}: {
  onContext: (ctx: ReturnType<typeof useAuthContext>) => void;
}) {
  const ctx = useAuthContext();
  onContext(ctx);
  return (
    <div>
      <span data-testid="hydrated">{String(ctx.hydrated)}</span>
      <span data-testid="user">{ctx.user?.email ?? "none"}</span>
      <span data-testid="busy">{String(ctx.busy)}</span>
      <span data-testid="can-auth">{String(ctx.canUseAuthenticatedApi)}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("AuthProvider (bearer mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(cookieMode.authCookieMode).mockReturnValue(false);
    vi.mocked(storageLib.readStoredSession).mockReturnValue(null);
  });

  it("throws when useAuthContext is used outside AuthProvider", () => {
    function BadConsumer() {
      useAuthContext();
      return null;
    }

    // Suppress console.error from React error boundary
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<BadConsumer />)).toThrow(
      "useAuthContext must be used within AuthProvider",
    );
    spy.mockRestore();
  });

  it("hydrates from localStorage on mount in bearer mode", () => {
    vi.mocked(storageLib.readStoredSession).mockReturnValue(fakeStored);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    expect(screen.getByTestId("hydrated")).toHaveTextContent("true");
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
    expect(capturedCtx!.accessToken).toBe("at-stored");
    expect(capturedCtx!.refreshToken).toBe("rt-stored");
  });

  it("starts with null user when no stored session", () => {
    render(
      <AuthProvider>
        <AuthConsumer onContext={() => {}} />
      </AuthProvider>,
    );

    expect(screen.getByTestId("hydrated")).toHaveTextContent("true");
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(screen.getByTestId("can-auth")).toHaveTextContent("false");
  });

  it("login sets user, tokens and writes to storage", async () => {
    vi.mocked(authApi.loginWithEmail).mockResolvedValueOnce(fakeSession);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedCtx!.login("test@example.com", "password");
    });

    expect(authApi.loginWithEmail).toHaveBeenCalledWith({
      email: "test@example.com",
      password: "password",
    });
    expect(storageLib.writeStoredSession).toHaveBeenCalledWith({
      accessToken: "at-123",
      refreshToken: "rt-456",
      user: fakeUser,
    });
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
  });

  it("login re-throws parsed API error", async () => {
    vi.mocked(authApi.loginWithEmail).mockRejectedValueOnce(
      new Error("Invalid credentials"),
    );

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    await expect(
      act(async () => {
        await capturedCtx!.login("a@b.c", "wrong");
      }),
    ).rejects.toThrow("Invalid credentials");
  });

  it("register sets user and writes to storage", async () => {
    vi.mocked(authApi.registerAccount).mockResolvedValueOnce(fakeSession);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedCtx!.register("new@example.com", "password123", "New User");
    });

    expect(authApi.registerAccount).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
      full_name: "New User",
    });
    expect(storageLib.writeStoredSession).toHaveBeenCalled();
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
  });

  it("register re-throws parsed API error", async () => {
    vi.mocked(authApi.registerAccount).mockRejectedValueOnce(
      new Error("Email already exists"),
    );

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    await expect(
      act(async () => {
        await capturedCtx!.register("dup@example.com", "password123");
      }),
    ).rejects.toThrow("Email already exists");
  });

  it("completeOAuthExchange sets session", async () => {
    vi.mocked(authApi.exchangeOAuthCode).mockResolvedValueOnce(fakeSession);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    await act(async () => {
      await capturedCtx!.completeOAuthExchange("exchange-code");
    });

    expect(authApi.exchangeOAuthCode).toHaveBeenCalledWith("exchange-code");
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
  });

  it("logout clears state and storage", async () => {
    vi.mocked(storageLib.readStoredSession).mockReturnValue(fakeStored);

    // Mock window.location.assign
    const assignMock = vi.fn();
    Object.defineProperty(window, "location", {
      value: { assign: assignMock },
      writable: true,
    });

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    // Verify user is set
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");

    act(() => {
      capturedCtx!.logout();
    });

    expect(storageLib.clearStoredSession).toHaveBeenCalled();
    expect(csrfLib.setCsrfToken).toHaveBeenCalledWith(null);
    expect(assignMock).toHaveBeenCalledWith("/login");
  });

  it("busy is false after login completes", async () => {
    vi.mocked(authApi.loginWithEmail).mockResolvedValueOnce(fakeSession);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    // Initially not busy
    expect(screen.getByTestId("busy")).toHaveTextContent("false");

    await act(async () => {
      await capturedCtx!.login("a@b.c", "pass");
    });

    // After login completes, busy should be false
    expect(screen.getByTestId("busy")).toHaveTextContent("false");
  });

  it("canUseAuthenticatedApi is true when hydrated, user set, and accessToken exists", async () => {
    vi.mocked(authApi.loginWithEmail).mockResolvedValueOnce(fakeSession);

    let capturedCtx: ReturnType<typeof useAuthContext> | undefined;
    render(
      <AuthProvider>
        <AuthConsumer onContext={(c) => (capturedCtx = c)} />
      </AuthProvider>,
    );

    // Initially false — no user
    expect(screen.getByTestId("can-auth")).toHaveTextContent("false");

    await act(async () => {
      await capturedCtx!.login("test@example.com", "password");
    });

    expect(screen.getByTestId("can-auth")).toHaveTextContent("true");
  });
});

describe("AuthProvider (cookie mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(cookieMode.authCookieMode).mockReturnValue(true);
  });

  it("calls fetchAuthBootstrap on mount in cookie mode", async () => {
    vi.mocked(authApi.fetchAuthBootstrap).mockResolvedValueOnce({
      authenticated: true,
      auth_transport: "cookie",
      user: fakeUser,
      csrf_token: "csrf-abc",
    });

    render(
      <AuthProvider>
        <AuthConsumer onContext={() => {}} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("hydrated")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("test@example.com");
    expect(csrfLib.setCsrfToken).toHaveBeenCalledWith("csrf-abc");
  });

  it("handles bootstrap failure gracefully (stays logged out)", async () => {
    vi.mocked(authApi.fetchAuthBootstrap).mockRejectedValueOnce(
      new Error("network down"),
    );

    render(
      <AuthProvider>
        <AuthConsumer onContext={() => {}} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("hydrated")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });

  it("handles unauthenticated bootstrap response", async () => {
    vi.mocked(authApi.fetchAuthBootstrap).mockResolvedValueOnce({
      authenticated: false,
      auth_transport: "none",
      user: null,
      csrf_token: null,
    });

    render(
      <AuthProvider>
        <AuthConsumer onContext={() => {}} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("hydrated")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("none");
  });
});
