import { describe, expect, it } from "vitest";

import { mapBotDto } from "./bots";

describe("mapBotDto", () => {
  it("maps API fields to WorkspaceBot", () => {
    expect(
      mapBotDto({
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "Support",
        niche: "E-commerce",
        niche_id: "education",
        goal_type: "support",
        status: "active",
        updated_at: "2026-03-01T12:00:00.000Z",
      }),
    ).toEqual({
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Support",
      nicheId: "education",
      nicheLabel: "Education",
      goalType: "support",
      goalLabel: "Support",
      status: "active",
      updatedAt: "2026-03-01T12:00:00.000Z",
    });
  });

  it("preserves channel_pending from API", () => {
    expect(
      mapBotDto({
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "X",
        niche: null,
        niche_id: "education",
        goal_type: "support",
        status: "channel_pending",
        primary_channel: "telegram",
        updated_at: null,
      }).status,
    ).toBe("channel_pending");
  });

  it("normalizes unknown status to draft", () => {
    expect(
      mapBotDto({
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "X",
        niche: null,
        niche_id: "custom",
        goal_type: "support",
        status: "unknown",
        updated_at: null,
      }).status,
    ).toBe("draft");
  });

  it("uses fallback label for unknown niche id", () => {
    const bot = mapBotDto({
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "X",
      niche: null,
      niche_id: "legal",
      goal_type: "consulting",
      status: "archived",
      updated_at: null,
    });
    expect(bot.nicheLabel).toBe("legal");
    expect(bot.goalLabel).toBe("Consulting");
    expect(bot.status).toBe("archived");
  });
});
