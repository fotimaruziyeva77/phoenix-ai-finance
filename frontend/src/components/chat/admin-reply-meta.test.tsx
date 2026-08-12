import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BotTestChatLastMeta } from "@/hooks/useBotTestChat";

import { AdminReplyMeta } from "./admin-reply-meta";

describe("AdminReplyMeta", () => {
  it("renders nothing when meta is null", () => {
    const { container } = render(<AdminReplyMeta meta={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when meta has no displayable fields", () => {
    const meta: BotTestChatLastMeta = {
      model_name: null,
      latency_ms: null,
      tokens_total: null,
      cost_usd: null,
    };
    const { container } = render(<AdminReplyMeta meta={meta} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows model, tokens, latency, and cost only when provided", () => {
    const meta: BotTestChatLastMeta = {
      model_name: "gemini-2.5-flash",
      latency_ms: 120,
      tokens_total: 42,
      cost_usd: "0.000015",
    };
    render(<AdminReplyMeta meta={meta} />);
    const bar = screen.getByTestId("admin-reply-meta");
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveTextContent("gemini-2.5-flash");
    expect(bar).toHaveTextContent("42");
    expect(bar).toHaveTextContent("120");
    expect(bar).toHaveTextContent("$");
  });

  it("omits cost when cost_usd is not parseable", () => {
    const meta: BotTestChatLastMeta = {
      model_name: "m",
      latency_ms: 1,
      tokens_total: 1,
      cost_usd: "not-a-number",
    };
    const { container } = render(<AdminReplyMeta meta={meta} />);
    const bar = container.querySelector('[data-testid="admin-reply-meta"]');
    expect(bar).toBeTruthy();
    expect(bar).toHaveTextContent("m");
    expect(bar).not.toHaveTextContent("not-a-number");
    expect(bar).not.toHaveTextContent("Cost");
  });
});
