import { describe, expect, it } from "vitest";

import { mapLeadDetailDto } from "./lead-detail";
import { sampleLeadDetailDto } from "./lead-detail.fixtures";

describe("mapLeadDetailDto", () => {
  it("maps API snake_case to detail shape including collected_data_json", () => {
    const d = mapLeadDetailDto(sampleLeadDetailDto());
    expect(d.id).toBe("550e8400-e29b-41d4-a716-446655440000");
    expect(d.status).toBe("qualified");
    expect(d.temperature).toBe("warm");
    expect(d.leadScore).toBe(55);
    expect(d.collectedData).toEqual({ company: "Acme", seats: 12 });
    expect(d.sourceChannel).toBe("telegram");
    expect(d.phone).toBe("+15559876543");
  });

  it("normalizes invalid collected_data_json to null", () => {
    const d = mapLeadDetailDto(
      sampleLeadDetailDto({
        collected_data_json: [] as unknown as Record<string, unknown>,
      }),
    );
    expect(d.collectedData).toBeNull();
  });
});
