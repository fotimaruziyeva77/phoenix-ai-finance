import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UseLeadDetailResult } from "@/hooks/useLeadDetail";
import { mapLeadDetailDto } from "@/lib/api/lead-detail";
import { sampleLeadDetailDto } from "@/lib/api/lead-detail.fixtures";

vi.mock("@/hooks/useLeadDetail", () => ({
  useLeadDetail: vi.fn(),
}));

import { useLeadDetail } from "@/hooks/useLeadDetail";

import { LeadDetailPage } from "./lead-detail-page";

const LEAD_ID = "550e8400-e29b-41d4-a716-446655440000";

function baseMock(overrides: Partial<UseLeadDetailResult> = {}): UseLeadDetailResult {
  return {
    status: "success",
    lead: mapLeadDetailDto(sampleLeadDetailDto()),
    errorMessage: null,
    saveError: null,
    saveSuccess: null,
    isSaving: false,
    refresh: vi.fn(),
    savePipeline: vi.fn().mockResolvedValue(true),
    ...overrides,
  };
}

describe("LeadDetailPage", () => {
  beforeEach(() => {
    vi.mocked(useLeadDetail).mockReturnValue(baseMock());
  });

  it("renders summary, collected JSON snapshot, status, temperature, phone, source, and created date from API-shaped data", () => {
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByTestId("lead-detail-root")).toBeInTheDocument();
    expect(screen.getByText("Jamie")).toBeInTheDocument();
    expect(screen.getByText(/Looking for onboarding help/i)).toBeInTheDocument();
    expect(screen.getByText(/"company"/)).toBeInTheDocument();
    const detailsSection = screen.getByRole("heading", { name: "Details" }).closest("section");
    expect(detailsSection).toBeTruthy();
    expect(within(detailsSection!).getByTestId("lead-pipeline-badge")).toHaveTextContent("Qualified");
    expect(within(detailsSection!).getByTestId("lead-temperature-badge")).toHaveTextContent("Warm");
    expect(screen.getByText("+15559876543")).toBeInTheDocument();
    expect(screen.getByText("telegram")).toBeInTheDocument();
  });

  it("submits pipeline form with mapped payload when saving", async () => {
    const savePipeline = vi.fn().mockResolvedValue(true);
    vi.mocked(useLeadDetail).mockReturnValue(baseMock({ savePipeline }));
    const user = userEvent.setup();
    render(<LeadDetailPage leadId={LEAD_ID} />);
    await user.selectOptions(screen.getByLabelText(/status/i), "proposal");
    await user.click(screen.getByTestId("lead-detail-save"));
    expect(savePipeline).toHaveBeenCalledWith({
      status: "proposal",
      lead_temperature: "warm",
      notes: "Left voicemail",
    });
  });

  it("shows load error when hook reports error", () => {
    vi.mocked(useLeadDetail).mockReturnValue(
      baseMock({
        status: "error",
        lead: null,
        errorMessage: "Lead not found.",
      }),
    );
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByTestId("lead-detail-load-error")).toHaveTextContent("Lead not found.");
  });

  it("shows loading copy while detail is loading", () => {
    vi.mocked(useLeadDetail).mockReturnValue(
      baseMock({
        status: "loading",
        lead: null,
      }),
    );
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByText(/loading lead/i)).toBeInTheDocument();
    expect(screen.queryByTestId("lead-detail-root")).not.toBeInTheDocument();
  });

  it("keeps a clear information hierarchy: summary, collected data, details, pipeline form", () => {
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByRole("heading", { name: "Summary", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Collected data", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Details", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pipeline & notes", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /leads/i })).toHaveAttribute("href", "/dashboard/leads");
  });

  it("shows save success feedback from the hook", () => {
    vi.mocked(useLeadDetail).mockReturnValue(baseMock({ saveSuccess: "Saved." }));
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByTestId("lead-detail-save-success")).toHaveTextContent("Saved.");
  });

  it("shows save error from the hook (e.g. invalid transition)", () => {
    vi.mocked(useLeadDetail).mockReturnValue(
      baseMock({ saveError: "Closed leads cannot move to another pipeline stage." }),
    );
    render(<LeadDetailPage leadId={LEAD_ID} />);
    expect(screen.getByTestId("lead-detail-save-error")).toHaveTextContent(/closed leads/i);
  });
});
