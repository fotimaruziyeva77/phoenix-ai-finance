import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAuth } from "@/hooks/useAuth";

import { SuperadminGate } from "./superadmin-gate";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/components/auth/auth-session-loading", () => ({
  AuthSessionLoading: () => <div data-testid="auth-loading">loading</div>,
}));

const baseAuth = {
  accessToken: "t",
  refreshToken: "r",
  canUseAuthenticatedApi: true,
  busy: false,
  login: vi.fn(),
  register: vi.fn(),
  completeOAuthExchange: vi.fn(),
  logout: vi.fn(),
  refreshProfile: vi.fn(),
};

describe("SuperadminGate", () => {
  it("redirects customer_admin to dashboard", async () => {
    replaceMock.mockClear();
    vi.mocked(useAuth).mockReturnValue({
      ...baseAuth,
      user: {
        id: "1",
        email: "a@b.c",
        full_name: null,
        role: "customer_admin",
        is_active: true,
        is_verified: true,
        created_at: "",
        updated_at: "",
      },
      hydrated: true,
    });

    render(
      <SuperadminGate>
        <div>platform-only</div>
      </SuperadminGate>,
    );

    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("allows superadmin to render children (no redirect)", () => {
    replaceMock.mockClear();
    vi.mocked(useAuth).mockReturnValue({
      ...baseAuth,
      user: {
        id: "2",
        email: "sa@b.c",
        full_name: null,
        role: "superadmin",
        is_active: true,
        is_verified: true,
        created_at: "",
        updated_at: "",
      },
      hydrated: true,
    });

    render(
      <SuperadminGate>
        <div>platform-content</div>
      </SuperadminGate>,
    );

    expect(screen.getByText("platform-content")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
