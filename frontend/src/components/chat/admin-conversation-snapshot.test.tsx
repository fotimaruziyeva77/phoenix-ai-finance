import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AdminConversationSnapshot } from "./admin-conversation-snapshot";

const baseConv = {
  id: "cccccccc-cccc-4ccc-cccc-cccccccccccc",
  bot_id: "b1",
  owner_id: "550e8400-e29b-41d4-a716-446655440000",
  channel: null,
  status: "active",
  current_state: "qualification",
  detected_intent: "sales_interest",
  niche_id_snapshot: "education",
  last_user_message_at: null,
  last_assistant_message_at: null,
  created_at: "2026-03-01T12:00:00.000Z",
  updated_at: "2026-03-01T12:00:00.000Z",
};

describe("AdminConversationSnapshot", () => {
  it("renders nothing when conversation is null (no invented state)", () => {
    const { container } = render(<AdminConversationSnapshot conversation={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders owner-visible fields and hides underscore keys from the main list", () => {
    render(
      <AdminConversationSnapshot
        conversation={{
          ...baseConv,
          collected_data_json: {
            student_grade: "Grade 9",
            __orch_target_field: "subject",
            _qp_clar_round: 0,
          },
        }}
      />,
    );

    expect(screen.getByTestId("bot-test-chat-current-state")).toHaveTextContent("qualification");
    expect(screen.getByTestId("bot-test-chat-detected-intent")).toHaveTextContent("sales_interest");
    const fields = screen.getByTestId("bot-test-chat-collected-fields");
    expect(fields).toHaveTextContent("student grade");
    expect(fields).toHaveTextContent("Grade 9");
    expect(fields.textContent).not.toMatch(/orch_target|_qp_clar/);
    expect(screen.getByTestId("bot-test-chat-collected-technical")).toHaveTextContent("__orch_target_field");
  });

  it("shows empty captured-fields hint when only technical keys exist", () => {
    render(
      <AdminConversationSnapshot
        conversation={{
          ...baseConv,
          collected_data_json: { __orch_target_field: "student_grade" },
        }}
      />,
    );
    expect(screen.getByTestId("bot-test-chat-collected-empty")).toBeInTheDocument();
  });

  it("exposes full JSON in advanced block for audit", () => {
    render(
      <AdminConversationSnapshot
        conversation={{
          ...baseConv,
          collected_data_json: { slot_a: "x" },
        }}
      />,
    );
    expect(screen.getByTestId("bot-test-chat-collected-json")).toHaveTextContent('"slot_a"');
  });
});
