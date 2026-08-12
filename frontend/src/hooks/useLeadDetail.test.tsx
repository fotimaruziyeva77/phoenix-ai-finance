import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LeadDetail } from "@/lib/api/lead-detail";
import { mapLeadDetailDto } from "@/lib/api/lead-detail";
import { sampleLeadDetailDto } from "@/lib/api/lead-detail.fixtures";

const mockFetchLeadDetail = vi.fn();
const mockPatchLeadPipeline = vi.fn();

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(() => ({
    user: {
      id: "u1",
      email: "t@t.co",
      full_name: null,
      role: "customer_admin",
      is_active: true,
      is_verified: true,
      created_at: "",
      updated_at: "",
    },
    accessToken: "integration-test-token",
    refreshToken: null,
    canUseAuthenticatedApi: true,
    hydrated: true,
    busy: false,
    login: vi.fn(),
    register: vi.fn(),
    completeOAuthExchange: vi.fn(),
    logout: vi.fn(),
    refreshProfile: vi.fn(),
  })),
}));

vi.mock("@/lib/api/lead-detail", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/lead-detail")>("@/lib/api/lead-detail");
  return {
    ...actual,
    fetchLeadDetail: (...args: unknown[]) => mockFetchLeadDetail(...args),
    patchLeadPipeline: (...args: unknown[]) => mockPatchLeadPipeline(...args),
  };
});

import { useLeadDetail } from "./useLeadDetail";

const LEAD_ID = "550e8400-e29b-41d4-a716-446655440000";

function detail(overrides: Partial<ReturnType<typeof sampleLeadDetailDto>> = {}): LeadDetail {
  return mapLeadDetailDto(sampleLeadDetailDto(overrides));
}

describe("useLeadDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads lead detail for the owner session (opens detail)", async () => {
    const initial = detail({ status: "new", name: "Alex" });
    mockFetchLeadDetail.mockResolvedValueOnce(initial);

    const { result } = renderHook(() => useLeadDetail(LEAD_ID));

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(mockFetchLeadDetail).toHaveBeenCalledWith("integration-test-token", LEAD_ID);
    expect(result.current.lead?.name).toBe("Alex");
    expect(result.current.lead?.status).toBe("new");
    expect(result.current.errorMessage).toBeNull();
  });

  it("status update refreshes local lead from PATCH response (persists in UI state)", async () => {
    const initial = detail({ status: "new" });
    const afterSave = detail({ status: "qualified", lead_temperature: "hot", notes: "Ready" });
    mockFetchLeadDetail.mockResolvedValueOnce(initial);
    mockPatchLeadPipeline.mockResolvedValueOnce(afterSave);

    const { result } = renderHook(() => useLeadDetail(LEAD_ID));

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.lead?.status).toBe("new");

    let ok = false;
    await act(async () => {
      ok = await result.current.savePipeline({
        status: "qualified",
        lead_temperature: "hot",
        notes: "Ready",
      });
    });

    expect(ok).toBe(true);
    expect(mockPatchLeadPipeline).toHaveBeenCalledWith("integration-test-token", LEAD_ID, {
      status: "qualified",
      lead_temperature: "hot",
      notes: "Ready",
    });
    expect(result.current.lead?.status).toBe("qualified");
    expect(result.current.lead?.temperature).toBe("hot");
    expect(result.current.lead?.notes).toBe("Ready");
    expect(result.current.saveSuccess).toBe("Saved.");
  });

  it("maps 404 to a safe not-found message (non-owner / unknown id)", async () => {
    const { ApiError } = await import("@/lib/api/client");
    mockFetchLeadDetail.mockRejectedValueOnce(new ApiError(404, "{}"));

    const { result } = renderHook(() => useLeadDetail(LEAD_ID));

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.lead).toBeNull();
    expect(result.current.errorMessage).toBe("Lead not found.");
  });

  it("surfaces 409 transition errors on save without mutating lead", async () => {
    const initial = detail({ status: "won" });
    mockFetchLeadDetail.mockResolvedValueOnce(initial);
    const { ApiError } = await import("@/lib/api/client");
    mockPatchLeadPipeline.mockRejectedValueOnce(
      new ApiError(
        409,
        JSON.stringify({
          error: {
            code: "lead_invalid_status_transition",
            message: "Closed leads cannot move to another pipeline stage.",
            category: "leads",
          },
        }),
      ),
    );

    const { result } = renderHook(() => useLeadDetail(LEAD_ID));

    await waitFor(() => expect(result.current.status).toBe("success"));

    await act(async () => {
      await result.current.savePipeline({
        status: "contacted",
        lead_temperature: null,
        notes: null,
      });
    });

    expect(result.current.lead?.status).toBe("won");
    expect(result.current.saveError).toContain("Closed leads");
  });
});
