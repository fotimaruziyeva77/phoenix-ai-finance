import { describe, expect, it } from "vitest";

import { mapLeadListItemDto } from "./leads";
import { sampleLeadListItemDto } from "./leads.fixtures";

describe("mapLeadListItemDto", () => {
  it("maps known pipeline statuses and normalizes unknown status to new", () => {
    const qualified = mapLeadListItemDto(sampleLeadListItemDto({ status: "qualified" }));
    expect(qualified.status).toBe("qualified");

    const weird = mapLeadListItemDto(sampleLeadListItemDto({ status: "not_a_real_stage" }));
    expect(weird.status).toBe("new");
  });

  it("maps temperature only for cold, warm, hot", () => {
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_temperature: "hot" })).temperature).toBe("hot");
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_temperature: null })).temperature).toBeNull();
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_temperature: "tepid" })).temperature).toBeNull();
  });

  it("maps lead_score to leadScore when in 0–100", () => {
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: 72 })).leadScore).toBe(72);
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: 0 })).leadScore).toBe(0);
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: 100 })).leadScore).toBe(100);
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: 72.6 })).leadScore).toBe(73);
  });

  it("treats out-of-range or missing scores as null", () => {
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: null })).leadScore).toBeNull();
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: 101 })).leadScore).toBeNull();
    expect(mapLeadListItemDto(sampleLeadListItemDto({ lead_score: -1 })).leadScore).toBeNull();
  });

  it("derives displayTitle from name, else first summary line, else Untitled", () => {
    expect(mapLeadListItemDto(sampleLeadListItemDto({ name: "  Ada  ", summary: "x" })).displayTitle).toBe("Ada");
    const fromSummary = mapLeadListItemDto(sampleLeadListItemDto({ name: null, summary: "Line one\nLine two" }));
    expect(fromSummary.displayTitle).toBe("Line one");
    expect(mapLeadListItemDto(sampleLeadListItemDto({ name: null, summary: null })).displayTitle).toBe("Untitled lead");
  });
});
