import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { KnowledgeFileListItemDto } from "@/lib/api/bot-knowledge";

import { KnowledgeFileList } from "./knowledge-file-list";

/** Minimal valid list row as returned by ``GET /bots/{id}/knowledge/files`` (no client-side inventions). */
function row(overrides: Partial<KnowledgeFileListItemDto>): KnowledgeFileListItemDto {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    bot_id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
    original_filename: "manual.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 2048,
    processing_status: "ready",
    processing_error: null,
    page_count: 5,
    uploaded_at: "2026-04-01T10:00:00.000Z",
    updated_at: "2026-04-01T10:10:00.000Z",
    ...overrides,
  };
}

describe("KnowledgeFileList", () => {
  it("shows empty state when API returns no items", () => {
    render(<KnowledgeFileList items={[]} loading={false} />);
    expect(screen.getByTestId("knowledge-file-list-empty")).toBeInTheDocument();
    expect(screen.getByText(/No knowledge files yet/i)).toBeInTheDocument();
  });

  it("shows loading line only when loading and list is still empty", () => {
    render(<KnowledgeFileList items={[]} loading />);
    expect(screen.queryByTestId("knowledge-file-list-empty")).not.toBeInTheDocument();
    expect(screen.getByText(/Loading knowledge files/i)).toBeInTheDocument();
  });

  it("renders rows from API items with filenames and status labels", () => {
    const items = [
      row({ id: "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa", original_filename: "a.pdf", processing_status: "ready" }),
      row({
        id: "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
        original_filename: "b.pdf",
        processing_status: "processing",
      }),
    ];
    render(<KnowledgeFileList items={items} />);
    expect(screen.getByTestId("knowledge-file-row-aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")).toBeInTheDocument();
    expect(screen.getByTestId("knowledge-file-row-bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb")).toBeInTheDocument();
    expect(screen.getByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("b.pdf")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("maps all processing_status values to user-facing labels", () => {
    const items = [
      row({ id: "01", processing_status: "uploaded" }),
      row({ id: "02", processing_status: "processing" }),
      row({ id: "03", processing_status: "ready" }),
      row({ id: "04", processing_status: "failed" }),
    ];
    render(<KnowledgeFileList items={items} />);
    expect(screen.getByText("Queued")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("shows server processing_error only when present on the DTO", () => {
    const ok = row({
      id: "ok-id",
      processing_status: "ready",
      processing_error: null,
    });
    const bad = row({
      id: "bad-id",
      processing_status: "failed",
      processing_error: "Text extraction timed out.",
    });
    render(<KnowledgeFileList items={[ok, bad]} />);
    expect(screen.queryByTestId("knowledge-file-error-ok-id")).not.toBeInTheDocument();
    expect(screen.getByTestId("knowledge-file-error-bad-id")).toHaveTextContent("Text extraction timed out.");
  });

  it("shows page count from API or em dash when null", () => {
    render(
      <KnowledgeFileList
        items={[
          row({ id: "p1", page_count: 42 }),
          row({ id: "p2", page_count: null }),
        ]}
      />,
    );
    expect(screen.getByText("42 pages")).toBeInTheDocument();
    expect(screen.getByText("Pages —")).toBeInTheDocument();
  });
});
