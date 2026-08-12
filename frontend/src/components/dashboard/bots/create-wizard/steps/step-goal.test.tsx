import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";
import { GOAL_OPTIONS } from "@/lib/create-bot-wizard/options";

import { StepGoal } from "./step-goal";

describe("StepGoal", () => {
  it("renders exactly 4 goal cards from config", () => {
    const html = renderToStaticMarkup(
      <StepGoal draft={createDefaultDraft()} updateDraft={vi.fn()} />,
    );
    expect(GOAL_OPTIONS).toHaveLength(4);
    for (const option of GOAL_OPTIONS) {
      expect(html).toContain(`data-testid="goal-card-${option.id}"`);
      expect(html).toContain(option.label);
      expect(html).toContain(option.hint);
    }
  });

  it("marks selected goal card state clearly", () => {
    const draft = { ...createDefaultDraft(), goalId: "sales" };
    const html = renderToStaticMarkup(<StepGoal draft={draft} updateDraft={vi.fn()} />);
    expect(html).toContain('value="sales"');
    expect(html).toContain("checked");
    expect(html).toContain('data-selected="true"');
  });
});
