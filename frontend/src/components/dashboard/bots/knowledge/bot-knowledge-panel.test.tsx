import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { BotKnowledgePanel } from "./bot-knowledge-panel";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ accessToken: "unit-test-token", hydrated: true }),
}));

vi.mock("@/lib/api/bot-knowledge", () => ({
  fetchBotKnowledgeFiles: vi.fn(),
  uploadBotKnowledgePdf: vi.fn(),
}));

import type { KnowledgeFileListItemDto } from "@/lib/api/bot-knowledge";
import { fetchBotKnowledgeFiles, uploadBotKnowledgePdf } from "@/lib/api/bot-knowledge";

function listItem(overrides: Partial<KnowledgeFileListItemDto>): KnowledgeFileListItemDto {
  return {
    id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    bot_id: "bot-int",
    original_filename: "policy.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 4096,
    processing_status: "ready",
    processing_error: null,
    page_count: 3,
    uploaded_at: "2026-04-02T08:00:00.000Z",
    updated_at: "2026-04-02T08:05:00.000Z",
    ...overrides,
  };
}

describe("BotKnowledgePanel", () => {
  beforeEach(() => {
    vi.mocked(fetchBotKnowledgeFiles).mockReset();
    vi.mocked(uploadBotKnowledgePdf).mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("renders upload UI and list chrome", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    render(<BotKnowledgePanel botId="bot-int" />);
    expect(screen.getByTestId("bot-knowledge-panel")).toBeInTheDocument();
    expect(screen.getByLabelText(/Upload PDF knowledge file/i)).toBeInTheDocument();
    await waitFor(() => expect(fetchBotKnowledgeFiles).toHaveBeenCalledWith("unit-test-token", "bot-int"));
  });

  it("loads and displays file list from API response only", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({
      items: [
        listItem({
          id: "f1111111-1111-4111-8111-111111111111",
          original_filename: "Alpha.pdf",
          processing_status: "ready",
        }),
        listItem({
          id: "f2222222-2222-4222-8222-222222222222",
          original_filename: "Beta.pdf",
          processing_status: "processing",
        }),
      ],
      total: 2,
    });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByText("Alpha.pdf")).toBeInTheDocument());
    expect(screen.getByText("Beta.pdf")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByTestId("knowledge-total-count")).toHaveTextContent("2 files total");
  });

  it("shows empty state when API returns zero items", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-file-list-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("knowledge-total-count")).not.toBeInTheDocument();
  });

  it("shows load error when list fetch fails", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockRejectedValue(new ApiError(403, "{}"));
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-load-error")).toBeInTheDocument());
    expect(screen.getByTestId("knowledge-load-error")).toHaveTextContent(/access/i);
  });

  it("shows client-side validation error for non-PDF without calling upload API", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByLabelText(/Upload PDF knowledge file/i)).toBeInTheDocument());
    // Wrong extension (even if MIME claims PDF) — matches real validation, avoids `accept` filtering in jsdom.
    const file = new File(["hello"], "readme.doc", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/Upload PDF knowledge file/i), file);
    expect(uploadBotKnowledgePdf).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByTestId("knowledge-upload-error")).toHaveTextContent(/\.pdf/i));
  });

  it("shows API upload error after server rejects PDF", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(uploadBotKnowledgePdf).mockRejectedValue(
      new ApiError(
        400,
        JSON.stringify({
          error: { message: "File is too large. Maximum size is 1000 bytes.", code: "validation_error" },
        }),
      ),
    );
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByLabelText(/Upload PDF knowledge file/i)).toBeInTheDocument());
    const file = new File(["%PDF-1.4 minimal"], "ok.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/Upload PDF knowledge file/i), file);
    await waitFor(() =>
      expect(screen.getByTestId("knowledge-upload-error")).toHaveTextContent(/too large/i),
    );
    expect(uploadBotKnowledgePdf).toHaveBeenCalledWith("unit-test-token", "bot-int", file);
  });

  it("refetch list on Refresh without inventing rows", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(fetchBotKnowledgeFiles).toHaveBeenCalledTimes(1));
    await user.click(screen.getByTestId("knowledge-refresh-list"));
    await waitFor(() => expect(fetchBotKnowledgeFiles).toHaveBeenCalledTimes(2));
  });

  it("shows polling note while any item is queued or processing", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({
      items: [listItem({ processing_status: "uploaded" })],
      total: 1,
    });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-polling-note")).toBeInTheDocument());
  });

  it("schedules background refresh while items are processing (interval registered)", async () => {
    const intervalSpy = vi.spyOn(globalThis, "setInterval");
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({
      items: [listItem({ processing_status: "processing" })],
      total: 1,
    });
    render(<BotKnowledgePanel botId="bot-int" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-polling-note")).toBeInTheDocument());
    const pollRegistration = intervalSpy.mock.calls.find((c) => c[1] === 4000);
    expect(pollRegistration).toBeDefined();
    intervalSpy.mockRestore();
  });

  it("hides upload zone when uploadsDisabled", async () => {
    vi.mocked(fetchBotKnowledgeFiles).mockResolvedValue({ items: [], total: 0 });
    render(<BotKnowledgePanel botId="bot-int" uploadsDisabled />);
    await waitFor(() => expect(screen.queryByLabelText(/Upload PDF knowledge file/i)).not.toBeInTheDocument());
    expect(screen.getByText(/Uploads are disabled while this bot is archived/i)).toBeInTheDocument();
  });
});
