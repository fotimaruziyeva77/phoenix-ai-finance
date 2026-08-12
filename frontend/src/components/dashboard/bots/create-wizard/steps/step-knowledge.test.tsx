import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { createDefaultDraft } from "@/lib/create-bot-wizard/default-draft";

import { StepKnowledge } from "./step-knowledge";

const mockT = (key: string) => {
  const map: Record<string, string> = {
    "dashboard.wizard.knowledgeHint": "Knowledge gives the bot trusted business context.",
    "dashboard.wizard.typicalSources": "Typical sources",
    "dashboard.wizard.srcPdf": "PDF documents",
    "dashboard.wizard.srcFaq": "FAQ documents",
    "dashboard.wizard.srcService": "Service information",
    "dashboard.wizard.srcPricing": "Pricing info",
    "dashboard.wizard.uploadDropTitle": "Drop PDF files here or click to browse",
    "dashboard.wizard.uploadDropMeta": "PDF only · Max 20 MB per file",
    "dashboard.wizard.removeFile": "Remove",
    "dashboard.wizard.fileTooLarge": "File is too large (max 20 MB)",
    "dashboard.wizard.fileNotPdf": "Only PDF files are accepted",
    "dashboard.wizard.pendingUploadNote": "Files will be uploaded automatically after bot creation",
    "dashboard.wizard.notesLabel": "Notes",
    "dashboard.wizard.notesHelp": "Add URLs or key facts now if you want.",
    "dashboard.wizard.notesPlaceholder": "e.g. Pricing page URL...",
    "dashboard.wizard.optional": "(optional)",
  };
  return map[key] ?? key;
};

describe("StepKnowledge", () => {
  it("explains knowledge source types clearly", () => {
    const html = renderToStaticMarkup(
      <StepKnowledge
        draft={createDefaultDraft()}
        updateDraft={vi.fn()}
        t={mockT}
        pendingFiles={[]}
        onAddFile={vi.fn(() => ({ ok: true, reason: null }))}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(html).toContain("PDF documents");
    expect(html).toContain("FAQ documents");
    expect(html).toContain("Service information");
    expect(html).toContain("Pricing info");
  });

  it("renders the upload zone for PDF files", () => {
    const html = renderToStaticMarkup(
      <StepKnowledge
        draft={createDefaultDraft()}
        updateDraft={vi.fn()}
        t={mockT}
        pendingFiles={[]}
        onAddFile={vi.fn(() => ({ ok: true, reason: null }))}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(html).toContain('data-testid="knowledge-upload-zone"');
    expect(html).toContain("Drop PDF files here or click to browse");
    expect(html).toContain("PDF only");
  });

  it("shows pending files list when files are selected", () => {
    const mockFile = new File(["content"], "test-doc.pdf", { type: "application/pdf" });
    Object.defineProperty(mockFile, "size", { value: 1024 * 500 }); // 500 KB

    const html = renderToStaticMarkup(
      <StepKnowledge
        draft={createDefaultDraft()}
        updateDraft={vi.fn()}
        t={mockT}
        pendingFiles={[mockFile]}
        onAddFile={vi.fn(() => ({ ok: true, reason: null }))}
        onRemoveFile={vi.fn()}
      />,
    );
    expect(html).toContain('data-testid="knowledge-pending-files"');
    expect(html).toContain("test-doc.pdf");
    expect(html).toContain("Files will be uploaded automatically after bot creation");
  });
});
