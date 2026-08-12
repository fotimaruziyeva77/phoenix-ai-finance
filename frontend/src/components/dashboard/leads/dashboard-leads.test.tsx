import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UseWorkspaceLeadsResult } from "@/hooks/useWorkspaceLeads";
import { mapLeadListItemDto } from "@/lib/api/leads";
import { sampleLeadListItemDto } from "@/lib/api/leads.fixtures";

vi.mock("@/hooks/useWorkspaceLeads", () => ({
  useWorkspaceLeads: vi.fn(),
}));

import { useWorkspaceLeads } from "@/hooks/useWorkspaceLeads";

import { DashboardLeads } from "./dashboard-leads";

function baseMock(overrides: Partial<UseWorkspaceLeadsResult> = {}): UseWorkspaceLeadsResult {
  return {
    status: "success",
    leads: [],
    total: 0,
    endpointUnavailable: false,
    errorMessage: null,
    refetch: vi.fn(),
    ...overrides,
  };
}

describe("DashboardLeads", () => {
  beforeEach(() => {
    vi.mocked(useWorkspaceLeads).mockReturnValue(baseMock());
  });

  it("shows loading skeleton for loading state", () => {
    vi.mocked(useWorkspaceLeads).mockReturnValue(baseMock({ status: "loading" }));
    render(<DashboardLeads />);
    expect(screen.getByTestId("leads-list-skeleton")).toBeInTheDocument();
    expect(screen.queryByTestId("leads-list-shell")).not.toBeInTheDocument();
  });

  it("shows loading skeleton for idle state (before first fetch completes)", () => {
    vi.mocked(useWorkspaceLeads).mockReturnValue(baseMock({ status: "idle" }));
    render(<DashboardLeads />);
    expect(screen.getByTestId("leads-list-skeleton")).toBeInTheDocument();
  });

  it("renders leads from hook data (API-shaped via mapLeadListItemDto)", () => {
    const row = mapLeadListItemDto(
      sampleLeadListItemDto({
        name: "Casey",
        status: "proposal",
        lead_temperature: "warm",
        lead_score: 64,
        phone: "+15551234567",
      }),
    );
    vi.mocked(useWorkspaceLeads).mockReturnValue(
      baseMock({
        leads: [row],
        total: 1,
      }),
    );
    render(<DashboardLeads />);
    expect(screen.getByTestId("leads-list-shell")).toBeInTheDocument();
    const table = screen.getByTestId("leads-list-table");
    const dataRow = within(table).getByTestId("leads-list-row");
    expect(within(dataRow).getByText("Casey")).toBeInTheDocument();
    expect(within(dataRow).getByText("Proposal")).toBeInTheDocument();
    expect(within(dataRow).getByText("Warm")).toBeInTheDocument();
    expect(within(dataRow).getByTestId("lead-score-cell")).toHaveTextContent("64");
    expect(within(dataRow).getByText("+15551234567")).toBeInTheDocument();
    expect(screen.getByTestId("leads-total-count")).toHaveTextContent("1 lead");
  });

  it("shows global empty state when success with zero leads and no filters", () => {
    vi.mocked(useWorkspaceLeads).mockReturnValue(baseMock({ status: "success", leads: [], total: 0 }));
    render(<DashboardLeads />);
    expect(screen.getByTestId("leads-empty-state")).toBeInTheDocument();
    expect(screen.getByText(/No leads yet/i)).toBeInTheDocument();
  });

  it("shows filtered empty state when filters are active and list is empty", async () => {
    const user = userEvent.setup();
    vi.mocked(useWorkspaceLeads).mockReturnValue(baseMock({ status: "success", leads: [], total: 0 }));
    render(<DashboardLeads />);
    await user.selectOptions(screen.getByLabelText(/pipeline status/i), "won");
    expect(screen.getByTestId("leads-empty-filtered")).toBeInTheDocument();
    expect(screen.getByText(/No leads match these filters/i)).toBeInTheDocument();
  });

  it("shows endpoint-unavailable empty state when API is not deployed", () => {
    vi.mocked(useWorkspaceLeads).mockReturnValue(
      baseMock({ status: "success", leads: [], total: 0, endpointUnavailable: true }),
    );
    render(<DashboardLeads />);
    expect(screen.getByText(/Leads API not available/i)).toBeInTheDocument();
  });

  it("shows error banner with retry when load fails", async () => {
    const refetch = vi.fn();
    vi.mocked(useWorkspaceLeads).mockReturnValue(
      baseMock({
        status: "error",
        errorMessage: "Could not load leads. Check your connection and try again.",
        refetch,
      }),
    );
    const user = userEvent.setup();
    render(<DashboardLeads />);
    expect(screen.getByTestId("leads-error-banner")).toBeInTheDocument();
    expect(screen.getByText(/Could not load leads/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("shows cap note when total exceeds loaded page size", () => {
    const one = mapLeadListItemDto(sampleLeadListItemDto({ id: "550e8400-e29b-41d4-a716-446655440000" }));
    vi.mocked(useWorkspaceLeads).mockReturnValue(
      baseMock({
        leads: [one],
        total: 150,
      }),
    );
    render(<DashboardLeads />);
    expect(screen.getByText(/Showing 1 on this page/i)).toBeInTheDocument();
  });
});
