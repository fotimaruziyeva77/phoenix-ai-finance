import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mapLeadListItemDto } from "@/lib/api/leads";
import { sampleLeadListItemDto } from "@/lib/api/leads.fixtures";

import { LeadsList } from "./leads-list";

describe("LeadsList", () => {
  it("renders status, temperature, and score from mapped API rows (no hard-coded fake workspace shape)", () => {
    const lead = mapLeadListItemDto(
      sampleLeadListItemDto({
        status: "qualified",
        lead_temperature: "cold",
        lead_score: 42,
        name: "River",
        niche_id: "dev_agency",
      }),
    );
    render(<LeadsList leads={[lead]} />);

    const table = screen.getByTestId("leads-list-table");
    const row = within(table).getByTestId("leads-list-row");
    expect(within(row).getByText("River")).toBeInTheDocument();
    expect(within(row).getByText("Qualified")).toBeInTheDocument();
    expect(within(row).getByText("Cold")).toBeInTheDocument();
    expect(within(row).getByTestId("lead-score-cell")).toHaveTextContent("42");

    const card = screen.getByTestId("leads-list-card");
    expect(within(card).getByTestId("lead-score-card")).toHaveTextContent("42");
  });

  it("shows em dash for missing temperature and score", () => {
    const lead = mapLeadListItemDto(
      sampleLeadListItemDto({
        lead_temperature: null,
        lead_score: null,
        name: "Minimal",
      }),
    );
    render(<LeadsList leads={[lead]} />);
    const row = screen.getByTestId("leads-list-row");
    const dashes = within(row).getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});
